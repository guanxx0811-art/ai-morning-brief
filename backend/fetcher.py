"""抓取模块：先独立 web_search 拿真实链接 → GLM 总结（链接受限）→ 交叉校验。

【架构说明】（v2 升级，2026-07-03）
两步法防幻觉：
  1. 调独立 web_search API 拿"真实链接 + 标题 + 正文 + 来源 + 日期"。
     引擎：search_pro_quark / search_pro_sogou（仅这两个返回真实 link）。
     中英文双语查询：中文走 quark+sogou，英文走 quark 补充国际源。
     注意：search_domain_filter 参数无效（实测被静默忽略），改为 prompt 强调优先源。
  2. 把带真实链接的素材喂给 GLM 总结，用 source_index 引用，映射回真实链接。
  3. 交叉校验 + 标题重叠率校验（防幻觉加强）。
  4. 来源分级（source_tier）：一手源/权威媒体/AI垂直/研究/中文源/聚合。

单独运行验证：
    cd D:\\开发\\ai-morning-brief
    python -m backend.fetcher
"""
import json
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import date

from zhipuai import ZhipuAI

from backend.config import ZHIPU_API_KEY, MODEL_NAME

# ============================================================
# 7 个固定分类（模型只能从这 7 类选，不许自创）
# ============================================================
CATEGORIES = [
    "大模型/新发布",
    "芯片/算力",
    "AI工具/产品",
    "公司/资本",
    "政策/监管/安全",
    "研究/突破",
    "行业应用",
]

# ============================================================
# 搜索引擎（仅这两个返回真实 link）
# ============================================================
SEARCH_ENGINES = ["search_pro_quark", "search_pro_sogou"]

# ============================================================
# 双语查询：中文覆盖国产/政策，英文补充国际前沿
# ============================================================
SEARCH_QUERIES_CN = [
    "AI 大模型 发布 新版本 最新进展",
    "人工智能 芯片 算力 数据中心 GPU",
    "AI 政策 法规 监管 安全 行业应用",
    "AI 工具 产品 应用 新功能 上线 发布",
]
SEARCH_QUERIES_EN = [
    "AI model launch release news July 2026",
    "AI startup funding acquisition 2026",
    "AI tool product launch new feature 2026",
]

# ============================================================
# 来源分级：域名 → tier
# ============================================================
SOURCE_TIERS = {
    # 一手源：公司官方博客
    "firsthand": [
        "openai.com", "anthropic.com", "deepmind.google", "ai.meta.com",
        "meta.com", "google.com", "microsoft.com", "nvidia.com",
        "x.ai", "zhipuai.cn", "deepseek.com", "tongyi.ai", "doubao.com",
        "github.com", "huggingface.co",
    ],
    # 权威国际媒体
    "authoritative": [
        "techcrunch.com", "venturebeat.com", "theverge.com",
        "arstechnica.com", "wired.com", "bloomberg.com",
        "reuters.com", "bbc.com", "nytimes.com",
    ],
    # AI 垂直聚合
    "vertical": [
        "the-decoder.com", "aiweekly.co", "therundown.ai",
        "artificialintelligence-news.com", "llm-stats.com",
    ],
    # 研究源
    "research": [
        "technologyreview.com", "deeplearning.ai", "syncedreview.com",
        "arxiv.org", "nature.com", "science.org",
    ],
    # 国内中文源
    "chinese": [
        "jiqizhixin.com", "qbitai.com", "36kr.com",
        "ithome.com", "cnbeta.com", "leiphone.com",
    ],
    # 其余自动归为 "aggregator"
}

# 反查表：domain → tier
_DOMAIN_TIER_MAP = {}
for _tier, _domains in SOURCE_TIERS.items():
    for _d in _domains:
        _DOMAIN_TIER_MAP[_d] = _tier


def _get_source_tier(domain: str) -> str:
    """根据域名返回来源等级。未匹配的归为 aggregator。"""
    return _DOMAIN_TIER_MAP.get(domain, "aggregator")


# ============================================================
# System Prompt（强化防幻觉 + 7 分类 + 权威源优先）
# ============================================================
SYSTEM_PROMPT = """你是一位资深 AI 行业分析师，负责整理每日 AI 资讯晨报。
你会收到一批带真实链接的搜索素材，需要从中筛选出最重要的 AI 资讯，按分类整理。

【铁律——违反任何一条，该条必须丢弃】
1. 每条资讯必须严格基于某条搜索素材的正文，标题和摘要必须有素材依据。
2. 如果素材中找不到某条信息的明确出处，宁可丢弃也不编造。
3. source_index 必须准确指向所引素材编号，不得随意填写。
4. 严禁编造新闻、编造链接、把无出处传言当新闻。

【分类规则】
只能从以下 7 类中选，不许自创分类名：
- 大模型/新发布：新模型、版本更新、benchmark 结果
- 芯片/算力：GPU、芯片、算力基建、数据中心
- AI工具/产品：面向用户的 AI 应用、产品、功能
- 公司/资本：融资、IPO、并购、人事、公司战略
- 政策/监管/安全：法规、AI 安全、对齐、网络安全
- 研究/突破：论文、学界、技术突破
- 行业应用：AI 在医疗/金融/交通/制造等垂直领域的落地

【来源优先级】
一手源（openai.com、anthropic.com 等公司官博）> 权威媒体（techcrunch、reuters）> AI 垂直站 > 中文源 > 聚合平台。
同一新闻多源出现 = 更可信，优先选取。
"""


def _item_get(it, key):
    """兼容 SearchResultResp 对象与 dict 两种形态取值。"""
    if isinstance(it, dict):
        return it.get(key)
    return getattr(it, key, None)


def _do_search(client, query, engine):
    """单次搜索，返回 [{title,link,content,media,publish_date}]（仅保留有 link 的）。"""
    try:
        resp = client.web_search.web_search(
            search_engine=engine,
            search_query=query,
            count=25,
            search_recency_filter="oneDay",
            content_size="medium",
        )
    except Exception as e:
        print(f"[search] {engine} '{query}' 出错: {e}")
        return []

    out = []
    for it in (getattr(resp, "search_result", None) or []):
        link = (_item_get(it, "link") or "").strip()
        if not link:
            continue
        out.append({
            "title": (_item_get(it, "title") or "").strip(),
            "link": link,
            "content": (_item_get(it, "content") or "").strip(),
            "media": (_item_get(it, "media") or "").strip(),
            "publish_date": (_item_get(it, "publish_date") or "").strip(),
        })
    return out


def gather_search_results(client):
    """多引擎多查询搜索（中英文双语），并发执行，按 link 去重合并，返回素材列表。"""
    # 构建全部 (query, engine) 搜索任务
    tasks = []
    # 中文查询走 quark + sogou
    for query in SEARCH_QUERIES_CN:
        for engine in SEARCH_ENGINES:
            tasks.append((query, engine))
    # 英文查询走 quark（sogou 对英文源几乎无效，省掉）
    for query in SEARCH_QUERIES_EN:
        tasks.append((query, "search_pro_quark"))

    # 并发执行所有搜索任务
    merged = {}  # link -> item
    with ThreadPoolExecutor(max_workers=min(8, len(tasks))) as pool:
        futures = [pool.submit(_do_search, client, q, e) for q, e in tasks]
        for fut in futures:
            for item in fut.result():
                if item["link"] not in merged:
                    merged[item["link"]] = item

    return list(merged.values())


def _extract_json(text: str) -> dict:
    """从模型输出中提取 JSON。"""
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(0))


def _summarize(client, results):
    """把带真实链接的素材喂给 GLM，精选 15-20 条按 7 分类整理。"""
    today = date.today().strftime("%Y-%m-%d")

    # 标注来源等级
    def tier_tag(r):
        domain = _domain_name(r["link"])
        tier = _get_source_tier(domain)
        labels = {
            "firsthand": "[一手源]",
            "authoritative": "[权威媒体]",
            "vertical": "[AI垂直]",
            "research": "[研究源]",
            "chinese": "[中文源]",
            "aggregator": "[聚合]",
        }
        return labels.get(tier, "")

    # 拼接素材
    lines = []
    for i, r in enumerate(results, 1):
        content_snippet = r["content"][:500].replace("\n", " ")
        tag = tier_tag(r)
        lines.append(
            f"[{i}] 标题：{r['title']}\n"
            f"来源：{r['media']} | 日期：{r['publish_date']} {tag}\n"
            f"链接：{r['link']}\n"
            f"正文：{content_snippet}"
        )
    material = "\n\n".join(lines)
    n = len(results)

    user_prompt = f"""今天是 {today}。以下是通过联网搜索得到的当日 AI 资讯素材（每条都含真实链接和来源等级）：

{material}

请基于以上素材，整理出 15-20 条最重要的 AI 资讯，按分类归类。要求：
1. 分类只能从以下 7 类选：{" / ".join(CATEGORIES)}。不许自创分类名。
2. 每条资讯必须严格引用某条素材，source_index 填素材编号（1-{n}）。标题和摘要必须能从所引素材正文中找到依据。无法溯源的坚决不要。
3. 摘要一两句话，基于所引素材正文提炼，不添加素材中没有的信息。
4. 标注了 [一手源] 或 [权威媒体] 的素材优先选取。[聚合] 素材次之。
5. 优先选择发布日期为今天({today})或昨天的素材，超过2天的不要选。
6. 质量优先于数量——如果确实没那么多可靠新闻，宁可少而准，不为凑数塞低质内容。
7. 分类配额：「AI工具/产品」这一类目标 5 条左右，优先从工具/产品类素材中选取。其余各类按素材实际情况 1-4 条即可，总数控制在 15-20 条。若工具/产品类可用素材不足 5 条，按实际可用数选取即可，不要为凑数编造或塞入低质内容。
8. 再写一段 overview，概括当天 AI 大事重点。

严格输出如下 JSON（不要任何解释、不要 markdown 代码块标记）：
{{
  "overview": "当天 AI 大事总览，一段话",
  "articles": [
    {{"title": "资讯标题", "summary": "一两句话摘要", "category": "大模型/新发布", "source_index": 1}}
  ]
}}"""

    resp = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
    )
    return _extract_json(resp.choices[0].message.content)


def _title_overlap(title_a: str, title_b: str) -> float:
    """两个标题的字符重叠率（Jaccard）。"""
    set_a = set(title_a)
    set_b = set(title_b)
    if not set_a or not set_b:
        return 0.0
    return len(set_a & set_b) / len(set_a | set_b)


def _build_articles(data, results):
    """映射回真实链接 + 交叉校验 + 防幻觉 + 来源分级。"""
    link_by_index = {i: r for i, r in enumerate(results, 1)}
    valid_links = {r["link"] for r in results}

    raw = data.get("articles") or []
    if not isinstance(raw, list):
        raw = []

    kept = []
    dropped = 0
    hallucination_dropped = 0
    for a in raw:
        idx = a.get("source_index")
        try:
            idx = int(idx)
        except (TypeError, ValueError):
            dropped += 1
            continue

        src = link_by_index.get(idx)
        if not src:
            dropped += 1
            continue

        url = src["link"]
        if url not in valid_links:
            dropped += 1
            continue

        # 防幻觉：标题重叠率校验
        model_title = (a.get("title") or "").strip()
        source_title = (src.get("title") or "").strip()
        overlap = _title_overlap(model_title, source_title)
        if overlap < 0.15 and source_title:
            print(f"[防幻觉] 丢弃：重叠率 {overlap:.0%} | 模型=\"{model_title[:25]}\" 素材=\"{source_title[:25]}\"")
            hallucination_dropped += 1
            continue

        domain = _domain_name(url)
        tier = _get_source_tier(domain)

        category = (a.get("category") or "").strip()
        if category not in CATEGORIES:
            # 尝试模糊匹配
            matched = False
            for c in CATEGORIES:
                if category in c or c.split("/")[0] in category:
                    category = c
                    matched = True
                    break
            if not matched:
                category = "行业应用"  # 兜底

        kept.append({
            "title": model_title or source_title or "（无标题）",
            "summary": (a.get("summary") or "").strip(),
            "category": category,
            "source_url": url,
            "source_name": src["media"] or domain,
            "source_domain": domain,
            "source_tier": tier,
            "publish_date": (src.get("publish_date") or "").strip(),
            "verified": True,
        })

    stats = {
        "raw": len(raw), "kept": len(kept), "dropped": dropped,
        "hallucination_dropped": hallucination_dropped,
        "search_results": len(valid_links),
    }
    return kept, stats


def _domain_name(url: str) -> str:
    """从 URL 取域名（如 techcrunch.com）。"""
    try:
        host = url.split("/")[2]
        return host[4:] if host.startswith("www.") else host
    except Exception:
        return ""


def fetch_brief() -> dict:
    """抓取一次当天 AI 资讯。

    返回 {overview, articles, stats, source_model}。
    """
    if not ZHIPU_API_KEY or ZHIPU_API_KEY == "在此填入你的智谱APIKey":
        raise RuntimeError("未配置 ZHIPU_API_KEY，请先在 backend/.env 填入真实密钥。")

    client = ZhipuAI(api_key=ZHIPU_API_KEY)

    results = gather_search_results(client)
    if not results:
        raise RuntimeError("搜索未返回任何带链接的结果，请检查引擎/网络/密钥。")
    print(f"[fetcher] 搜索到 {len(results)} 条带链接素材")

    data = _summarize(client, results)
    overview = (data.get("overview") or "").strip()

    articles, stats = _build_articles(data, results)

    return {
        "overview": overview,
        "articles": articles,
        "stats": stats,
        "source_model": MODEL_NAME,
    }


if __name__ == "__main__":
    print("=" * 60)
    print("AI 晨报 - 抓取模块测试")
    print("=" * 60)
    result = fetch_brief()
    print(f"\n【统计】{result['stats']}")
    print(f"\n【总览】\n{result['overview']}")
    print(f"\n【资讯 {len(result['articles'])} 条】")

    tier_labels = {
        "firsthand": "[一手]", "authoritative": "[权威]", "vertical": "[垂直]",
        "research": "[研究]", "chinese": "[中文]", "aggregator": "[转载]",
    }
    for i, a in enumerate(result["articles"], 1):
        tier_str = tier_labels.get(a["source_tier"], "[转载]")
        print(f"\n{i}. [{a['category']}] {a['title']}")
        print(f"   摘要: {a['summary'][:60]}")
        print(f"   {tier_str} | {a['source_name']} ({a['source_domain']}) | {a['publish_date']}")

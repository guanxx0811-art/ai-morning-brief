"""存储模块：将抓取结果写入 batches + articles 两表。

核心函数 save_batch(result)：
- 接收 fetcher.fetch_brief() 返回的 {overview, articles, stats, source_model}
- 生成 UUID batch_id，写入两表（事务保证原子性）
- 返回 batch_id
"""
import uuid
from datetime import datetime

from backend.db import get_connection


def save_batch(result: dict) -> str:
    """将一次抓取结果持久化到数据库。

    参数：
        result — fetcher.fetch_brief() 的返回值，含 overview / articles / stats / source_model

    返回：
        batch_id — 本次批次的 UUID

    逻辑：
        - batch_id 自动生成 UUID4
        - fetch_date 取当天日期（YYYY-MM-DD），fetch_timestamp 取写入时刻
        - articles 逐条写入，created_at 同 fetch_timestamp
        - 整体包在一个事务里，失败则回滚
    """
    batch_id = uuid.uuid4().hex
    now = datetime.now()
    fetch_date = now.strftime("%Y-%m-%d")
    fetch_timestamp = now.strftime("%Y-%m-%d %H:%M:%S")

    overview = result.get("overview", "")
    source_model = result.get("source_model", "")
    articles = result.get("articles", [])

    with get_connection() as conn:
        # 写入批次
        conn.execute(
            """
            INSERT INTO batches (batch_id, fetch_date, fetch_timestamp, overview,
                                 source_model, status, article_count)
            VALUES (?, ?, ?, ?, ?, 'success', ?)
            """,
            (batch_id, fetch_date, fetch_timestamp, overview,
             source_model, len(articles)),
        )

        # 写入每条资讯
        for a in articles:
            conn.execute(
                """
                INSERT INTO articles (batch_id, title, summary, category,
                                      source_url, source_name, source_domain,
                                      source_tier, publish_date, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (batch_id,
                 a.get("title", ""),
                 a.get("summary", ""),
                 a.get("category", ""),
                 a.get("source_url", ""),
                 a.get("source_name", ""),
                 a.get("source_domain", ""),
                 a.get("source_tier", ""),
                 a.get("publish_date", ""),
                 fetch_timestamp),
            )

        conn.commit()

    return batch_id

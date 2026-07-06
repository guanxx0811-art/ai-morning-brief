"""AI 晨报 — FastAPI 入口。

阶段 1 职责：
- 启动时建表（init_db）
- 提供健康检查接口 /api/health
- 托管前端静态文件（阶段 4 填充真实页面，当前为占位 index.html）

运行（在项目根目录 ai-morning-brief/ 下执行）：
    uvicorn backend.main:app --host 0.0.0.0 --port 8000
访问：
    电脑：http://localhost:8000
    手机：http://<本机IP>:8000  （需与电脑同一 WiFi）
接口文档（FastAPI 自带）：
    http://localhost:8000/docs
"""
import os

from datetime import date

from fastapi import FastAPI, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.config import HOST, PORT, DB_PATH, ZHIPU_API_KEY, MODEL_NAME
from backend.db import get_connection, init_db, list_tables
from backend.fetcher import fetch_brief
from backend.storage import save_batch

app = FastAPI(title="AI 晨报", description="每天 5 分钟，和世界 AI 对齐")


@app.on_event("startup")
def on_startup():
    """应用启动时：确保数据库与表存在。"""
    init_db()


@app.post("/api/fetch")
def api_fetch():
    """触发一次 AI 资讯抓取，存入数据库，返回批次信息。

    返回示例：
        {
          "batch_id": "a1b2c3d4...",
          "article_count": 12,
          "overview": "今天AI大事..."
        }
    """
    result = fetch_brief()
    batch_id = save_batch(result)
    return {
        "batch_id": batch_id,
        "article_count": result["stats"]["kept"],
        "overview": result["overview"],
    }


@app.get("/api/dates")
def api_dates():
    """返回数据库中有资讯的日期列表（降序，最新在前）。

    返回示例：{"dates": ["2026-07-03", "2026-07-02"]}
    """
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT DISTINCT fetch_date FROM batches "
            "WHERE status='success' ORDER BY fetch_date DESC"
        ).fetchall()
    return {"dates": [row["fetch_date"] for row in rows]}


@app.get("/api/brief")
def api_brief(date: str = Query(default=None, description="查询日期 YYYY-MM-DD，默认当天")):
    """获取指定日期最新批次的资讯。

    逻辑：取该日 fetch_timestamp 最大的成功批次，返回 overview + articles。
    如无数据返回空。
    """
    target = date or date.today().strftime("%Y-%m-%d")

    with get_connection() as conn:
        # 取当天最新批次
        batch = conn.execute(
            "SELECT batch_id, fetch_timestamp, overview, article_count "
            "FROM batches WHERE fetch_date=? AND status='success' "
            "ORDER BY fetch_timestamp DESC LIMIT 1",
            (target,),
        ).fetchone()

        if not batch:
            return {"date": target, "overview": "", "articles": [],
                    "fetch_timestamp": "", "article_count": 0}

        # 取该批次的所有资讯
        rows = conn.execute(
            "SELECT title, summary, category, source_url, source_name, source_domain, source_tier, publish_date "
            "FROM articles WHERE batch_id=? ORDER BY id",
            (batch["batch_id"],),
        ).fetchall()

    articles = [
        {
            "title": r["title"],
            "summary": r["summary"],
            "category": r["category"],
            "source_url": r["source_url"],
            "source_name": r["source_name"],
            "source_domain": r["source_domain"] or "",
            "source_tier": r["source_tier"] or "",
            "publish_date": r["publish_date"] or "",
        }
        for r in rows
    ]

    return {
        "date": target,
        "overview": batch["overview"],
        "articles": articles,
        "fetch_timestamp": batch["fetch_timestamp"],
        "article_count": batch["article_count"],
    }


@app.get("/api/health")
def health():
    """健康检查：确认服务可用、数据库已生成、表已建好、密钥是否已配置。

    返回示例：
        {
          "status": "ok",
          "db_exists": true,
          "db_path": ".../data/morning.db",
          "tables": ["articles", "batches"],
          "api_key_configured": true,
          "model": "glm-4.6"
        }
    """
    return {
        "status": "ok",
        "db_exists": os.path.exists(DB_PATH),
        "db_path": DB_PATH,
        "tables": list_tables(),
        "api_key_configured": bool(ZHIPU_API_KEY) and ZHIPU_API_KEY != "在此填入你的智谱APIKey",
        "model": MODEL_NAME,
    }


# ---- 前端静态文件托管 ----
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")

if os.path.isdir(FRONTEND_DIR):
    # /static/* 映射到 frontend/ 下的 css/js 等资源
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


@app.get("/")
def index():
    """根路径返回前端首页 index.html。"""
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))


if __name__ == "__main__":
    # 直接 python backend/main.py 也可启动（便于不熟悉 uvicorn 命令时使用）
    import uvicorn

    uvicorn.run("backend.main:app", host=HOST, port=PORT, reload=True)

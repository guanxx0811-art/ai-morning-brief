"""数据库模块：SQLite 连接与建表。

- 单文件 data/morning.db，零配置，适合本地 MVP。
- 启动时自动建表（CREATE TABLE IF NOT EXISTS）。
- 保留所有批次，不覆盖、不删——完整历史可追溯。
"""
import os
import sqlite3

from backend.config import DB_PATH


def get_connection():
    """返回一个 sqlite3 连接。

    row_factory 设为 sqlite3.Row，让查询结果可用列名访问（如 row['title']），
    比 tuple 下标更清晰。
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")  # 开启外键约束
    return conn


def init_db():
    """建表（如表不存在则创建）。应用启动时调用。

    表结构说明见项目方案文档。字段可按需扩展，这里是一期基础版。
    """
    # 确保数据目录存在
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

    with get_connection() as conn:
        conn.executescript(
            """
            -- 批次表：每次抓取 = 一个批次
            CREATE TABLE IF NOT EXISTS batches (
                batch_id        TEXT PRIMARY KEY,        -- 批次号 UUID
                fetch_date      TEXT NOT NULL,           -- 抓取日期 YYYY-MM-DD，按天查询
                fetch_timestamp TEXT NOT NULL,           -- 完整时间戳，判定"当天最新一次"
                overview        TEXT,                    -- 当天总览一段话
                source_model    TEXT,                    -- 用哪个模型抓的，备查
                status          TEXT,                    -- success / failed
                article_count   INTEGER DEFAULT 0        -- 本批次资讯条数
            );

            -- 资讯表：每条资讯
            CREATE TABLE IF NOT EXISTS articles (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                batch_id    TEXT NOT NULL,               -- 外键 -> batches.batch_id
                title       TEXT,                        -- 资讯标题
                summary     TEXT,                        -- 该条摘要
                category    TEXT,                        -- 分类：大模型/工具/公司动态/政策/研究
                source_url  TEXT NOT NULL,               -- 原文链接，必填（防幻觉核心）
                source_name TEXT,                        -- 来源站点名，可选
                source_domain TEXT,                      -- 来源域名（如 techcrunch.com）
                publish_date TEXT,                       -- 原文发布日期（来自搜索结果）
                created_at  TEXT,                        -- 存入时间
                FOREIGN KEY (batch_id) REFERENCES batches(batch_id)
            );

            -- 辅助索引：按日期取最新批次（fetch_date + fetch_timestamp）
            CREATE INDEX IF NOT EXISTS idx_batches_date_ts
                ON batches(fetch_date, fetch_timestamp);

            -- 辅助索引：按批次查资讯
            CREATE INDEX IF NOT EXISTS idx_articles_batch
                ON articles(batch_id);
            """
        )

    # 兼容已有数据库：若旧表缺少列则追加
    with get_connection() as conn:
        for col in ["publish_date", "source_domain", "source_tier"]:
            try:
                conn.execute(f"ALTER TABLE articles ADD COLUMN {col} TEXT")
                conn.commit()
            except Exception:
                pass  # 列已存在，忽略


def list_tables():
    """返回当前数据库里的所有表名（验证用）。"""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
        return [row["name"] for row in rows]

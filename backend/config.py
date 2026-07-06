"""配置模块：从 .env 读取密钥与运行参数。

设计原则：
- 密钥不硬编码进源码，统一放 backend/.env（参考 .env.example）。
- 路径基于本文件位置计算，无论从哪个目录启动都能正确定位。
"""
import os
from dotenv import load_dotenv

# backend/ 目录绝对路径
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# 项目根目录（backend 的上一层）
PROJECT_ROOT = os.path.dirname(BASE_DIR)

# 加载 backend/.env
load_dotenv(os.path.join(BASE_DIR, ".env"))

# ---- 智谱 API 配置 ----
ZHIPU_API_KEY = os.getenv("ZHIPU_API_KEY", "")
MODEL_NAME = os.getenv("MODEL_NAME", "glm-4.6")  # 已确认存在的模型 ID

# ---- 服务配置 ----
HOST = os.getenv("HOST", "0.0.0.0")  # 0.0.0.0 让局域网手机能访问
PORT = int(os.getenv("PORT", "8000"))

# ---- 数据库配置 ----
# SQLite 单文件，放项目根目录 data/ 下（运行时自动创建该目录）
DB_PATH = os.path.join(PROJECT_ROOT, "data", "morning.db")

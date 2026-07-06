# AI 晨报（一期）

每天 5 分钟，和世界 AI 对齐。AI 带搜索抓取当天 AI 大事 → 存 SQLite → H5 展示。

## 技术栈
- 前端：原生 HTML/CSS/JS（无构建工具）
- 后端：Python + FastAPI
- 数据库：SQLite（单文件 `data/morning.db`）
- AI：智谱 GLM-4.6 + web_search（联网搜索，返回真实原文链接）

## 目录结构
```
ai-morning-brief/
├── backend/
│   ├── main.py          # FastAPI 入口（路由 + 托管前端）
│   ├── config.py        # 读 .env 配置
│   ├── db.py            # SQLite 连接与建表
│   ├── fetcher.py       # 抓取模块（阶段2）
│   ├── schemas.py       # 数据模型（后续阶段）
│   ├── .env / .env.example
│   └── requirements.txt
├── frontend/            # H5 页面（阶段4）
├── data/morning.db      # SQLite 数据库（运行时生成）
└── README.md
```

## 首次准备（只需做一次）

### 1. 安装依赖（国内镜像）
```powershell
pip install -i https://mirrors.aliyun.com/pypi/simple/ -r D:\开发\ai-morning-brief\backend\requirements.txt
```

### 2. 配置密钥
```powershell
Copy-Item D:\开发\ai-morning-brief\backend\.env.example D:\开发\ai-morning-brief\backend\.env -Force
```
然后编辑 `backend/.env`，把 `ZHIPU_API_KEY` 改成你的真实智谱 API Key。

## 运行
在项目根目录下：
```powershell
cd D:\开发\ai-morning-brief
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

## 访问
- 电脑：http://localhost:8000
- 接口文档（Swagger）：http://localhost:8000/docs
- 健康检查：http://localhost:8000/api/health
- 手机（与电脑同一 WiFi）：http://<本机IP>:8000

### 查询本机 IP（手机访问用）
```powershell
ipconfig | Select-String "IPv4"
```
找到类似 `192.168.x.x` 的地址，手机浏览器输入 `http://192.168.x.x:8000`。

## 阶段进度
- [x] **阶段1 骨架+建表**：FastAPI 起服务、`/api/health`、数据库与表自动生成
- [x] **阶段2 抓取模块**：独立 web_search(quark/sogou 引擎)拿真实链接 → GLM-4.6 总结 → 交叉校验，防幻觉
- [ ] 阶段3 存储 + `/api/fetch`
- [ ] 阶段4 H5 展示
- [ ] 阶段5 联调

## 阶段1 验证方式
1. 起服务（见上"运行"）
2. 浏览器或命令行访问 `/api/health`，应返回 `status: ok`、`db_exists: true`、`tables: [articles, batches]`
3. 查看 `data/morning.db` 文件已生成

> `api_key_configured` 在填入真实密钥前为 false，属正常；阶段2 抓取前需先填好密钥。

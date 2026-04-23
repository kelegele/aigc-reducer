# 部署指南

## 文件清单

| 文件 | 说明 |
|------|------|
| `docker-compose.yml` | 三容器编排（db + backend + frontend） |
| `.env.example` | 生产环境变量模板，部署时复制为 `.env` 并填写 |
| `web/Dockerfile` | 后端镜像（Python 3.12 + uv） |
| `web/.dockerignore` | 排除 .env、.venv、tests 等 |
| `web/frontend/Dockerfile` | 前端多阶段构建（node build → nginx 托管） |
| `web/frontend/.dockerignore` | 排除 node_modules、dist、.env |
| `web/frontend/nginx.conf` | SPA 路由 + 反向代理 `/api` |

## 架构

```
┌─────────────────────────────────────────┐
│           Docker Compose                │
│                                         │
│  ┌──────────┐  ┌──────────┐  ┌───────┐ │
│  │ Frontend │  │ Backend  │  │  DB   │ │
│  │  (Nginx) │  │ (FastAPI)│  │ PGSQL │ │
│  │  :80/443 │  │  :9000   │  │ :5432 │ │
│  └──────────┘  └──────────┘  └───────┘ │
└─────────────────────────────────────────┘
```

- **Frontend**：`npm run build` 产物由 Nginx 托管静态文件 + 反向代理 `/api` 到后端
- **Backend**：Uvicorn 运行 FastAPI，启动时自动执行 `alembic upgrade head`
- **PostgreSQL**：持久化数据卷挂载（或用云厂商托管 PG）

## 部署流程

```bash
# 1. 克隆代码
git clone <repo-url> && cd aigc-reducer

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env，至少填写：DOMAIN、DB_PASSWORD、JWT_SECRET_KEY、支付宝密钥

# 3. 启动
docker compose up -d

# 4. 查看日志
docker compose logs -f
```

## Uvicorn Worker

初期单容器 2-4 Worker 即可，在 `docker-compose.yml` 的 `command` 中配置：

```bash
uvicorn aigc_web.main:app --workers 4 --port 9000
```

流量上来后再拆多容器 + Nginx 负载均衡。多 Worker 下每个进程独立内存和数据库连接，并发安全由数据库锁保证。

## 数据库连接池

生产环境需要配置连接池参数（`database.py`）：

```python
engine = create_engine(
    settings.DATABASE_URL,
    pool_size=10,       # 每个进程的常驻连接数
    max_overflow=20,    # 高峰期额外可开连接数
    pool_timeout=30,    # 获取连接超时秒数
)
```

## 并发安全

- 积分充值/消费：已用 `with_for_update()` 行级悲观锁
- 支付回调幂等：订单查询已加 `with_for_update()`，防止重复加积分
- 多 Worker 下并发安全由数据库锁保证，无需额外内存锁

## 注意事项

- 支付宝回调需要公网域名 + HTTPS，回调地址必须是 `https://`
- JWT_SECRET、ALIPAY_PRIVATE_KEY 等秘钥通过环境变量注入，不写进镜像
- 云服务器 2C4G 轻量云起步，域名备案后配 HTTPS（Let's Encrypt 免费证书）
- CLI 是本地工具，不需要部署到服务器
- `.dockerignore` 确保 `.env` 和 `node_modules` 不进入镜像
- 后端启动入口统一由 `docker-compose.yml` 的 `command` 控制（含 alembic 迁移），Dockerfile 不设 CMD

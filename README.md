# AIGC Reducer

降低学术论文 AIGC 查重率的工具。支持 CLI 和 Web 两种使用方式。

## 项目结构

```
aigc-reducer/
├── cli/                # CLI 工具（Python）
├── web/                # Web 服务后端（FastAPI）
│   ├── src/aigc_web/   #   Python 源码
│   ├── frontend/       #   React 前端
│   ├── alembic/        #   数据库迁移
│   └── tests/          #   后端测试（33 个）
├── docker-compose.yml  # Docker 部署
└── docs/superpowers/   # 设计文档和实现计划
```

## CLI 工具

交互式 CLI，逐步引导完成 AIGC 查重率降低：

```bash
cd cli && uv sync
uv run aigc-reduce
```

### 功能

- **双模式检测**：规则引擎（快速）或 LLM 反查（精准）
- **5 种改写风格**：学术人文化、口语化、文言文化、中英混杂化、粗犷草稿风
- **多格式输入**：`.docx` / `.doc` / `.pdf` / `.md`
- **多 LLM 供应商**：DeepSeek、通义千问、智谱、OpenAI、Anthropic 等
- **交互式逐段确认**：每个高风险段落提供 A/B 改写方案

详细用法见 [cli/README.md](cli/README.md)。

## Web 服务

手机号验证码登录 + 积分账户系统的 Web 应用。

### 快速开始

```bash
# 1. 启动 PostgreSQL
docker compose up -d db

# 2. 安装依赖 & 运行迁移
cd web && uv sync
uv run alembic upgrade head

# 3. 启动后端
uv run uvicorn aigc_web.main:app --reload --port 8000

# 4. 启动前端（另一个终端）
cd web/frontend && npm install && npm run dev
```

访问 http://localhost:5173 即可使用。

### API

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/health | 健康检查 |
| POST | /api/auth/sms/send | 发送验证码 |
| POST | /api/auth/login/phone | 手机号登录（自动注册） |
| POST | /api/auth/refresh | 刷新 token |
| GET | /api/auth/me | 当前用户信息 |

Swagger 文档：http://localhost:8000/docs

### 技术栈

**后端**: Python 3.12 + FastAPI + SQLAlchemy 2.0 + Alembic + JWT

**前端**: React 19 + TypeScript + Ant Design + Zustand + Axios + Vite

### 部署

```bash
docker compose up -d
```

自动启动 PostgreSQL + API 服务，并运行数据库迁移。

## 开发

```bash
# CLI 测试
cd cli && uv run pytest tests/ -v

# Web 后端测试
cd web && uv run pytest tests/ -v

# Web 前端构建
cd web/frontend && npm run build
```

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AIGC Reducer — 降低学术论文 AIGC 查重率的 CLI 工具 + Web 服务。通过检测 AI 写作特征并提供多种改写风格，降低知网、GoCheck 等平台的 AI 查重率。

## Monorepo Structure

- `cli/` — CLI 工具（Python），所有源码、测试、依赖配置均在此目录下
- `web/` — Web 服务后端（FastAPI + SQLAlchemy + Alembic）
- `web/frontend/` — Web 前端（React + TypeScript + Ant Design）
- `docs/superpowers/` — 设计文档和实现计划

## Development Commands

### CLI (from `cli/` directory)

```bash
# 安装依赖
uv sync

# 运行 CLI
uv run aigc-reduce

# 运行测试
uv run pytest tests/

# 运行测试（带覆盖率）
uv run pytest tests/ --cov=aigc_reducer

# 运行单个测试文件
uv run pytest tests/test_detector.py

# 运行单个测试用例
uv run pytest tests/test_detector.py::test_function_name -v
```

## Architecture

### 6-Step Interactive Workflow (cli.py)

输入文件 → 解析为段落 → 选择风格+检测模式 → 扫描风险 → (可选)全量语义重构 → 逐段 A/B 改写确认 → 输出三文件

### Core Components

- **parser.py** — 文档解析器，支持 .md/.docx/.doc/.pdf，输出 `Paragraph` dataclass 列表
- **detector.py** — 检测编排器，两种模式：
  - `rules` 模式：5 个规则检测器各 20% 权重求综合分
  - `llm` 模式：LLM 反查模拟商业平台判断
- **rewriter.py** — 改写编排器，管理 5 种风格的 aggressive/conservative 两档改写
- **llm_client.py** — LiteLLM 统一客户端，通过 `LLM_MODEL`/`LLM_API_KEY`/`LLM_BASE_URL` 环境变量配置
- **report.py** — Rich CLI 输出（扫描报告、进度、最终报告）

### Detection Modules (`detectors/`)

每个检测器独立实现，输入 `Paragraph`，输出 0-100 分：
- `perplexity.py` — 困惑度（用词标准化程度）
- `burstiness.py` — 突发性（句式长度方差）
- `connectors.py` — 模板化连接词频率
- `cognitive.py` — 认知特征（批判性思维标记）
- `semantic_fingerprint.py` — 语义指纹（AI 论证结构模式）
- `llm_detector.py` — LLM 反查（独立于上述 5 个，用于 llm 模式）

### Rewriting Styles (`styles/`)

所有风格继承 `base.py:RewriteStyle` 抽象类，实现 aggressive + conservative 两种 prompt：
- `academic_humanistic.py` — 学术人文化（默认推荐）
- `colloquial.py` — 口语化
- `classical.py` — 文言文化
- `mixed_en_zh.py` — 中英混杂化
- `rough_draft.py` — 粗犷草稿风

### Risk Levels

| 综合分 | 风险等级 |
|--------|---------|
| <10%   | 低风险   |
| 10-30% | 中风险   |
| 30-60% | 中高     |
| >60%   | 高风险   |

高于 30% 的段落会被标记为需处理。

## LLM Configuration

通过 `cli/.env` 文件配置（参考 `cli/.env.example`）。LLM 调用统一走 LiteLLM，模型标识格式为 `供应商/模型名`。`llm_client.py` 内置了各供应商默认 base_url，大部分情况只需配置 `LLM_MODEL` 和 `LLM_API_KEY`。

## Output Files

运行后在 `cli/output/` 生成三个文件：
- `*_reduced.md` — 改写后全文
- `*_diff.md` — 前后差异对比
- `*_revision_report.md` — 整改建议报告

## Key Patterns

- 所有 Python 操作通过 `uv`，不使用 pip/conda/venv
- Python >=3.10，使用 `str | None` 而非 `Optional[str]`
- 中文 docstring 和注释
- 检测器模块化：新增检测维度只需在 `detectors/` 下添加模块并在 `detector.py` 中注册
- 改写风格模块化：新增风格只需继承 `RewriteStyle` 并在 `rewriter.py` 中注册

## Web Service (from `web/` directory)

```bash
# 安装依赖
uv sync

# 启动后端（开发模式）
uv run uvicorn aigc_web.main:app --reload --port 8000

# 运行后端测试
uv run pytest tests/ -v

# 数据库迁移
uv run alembic revision --autogenerate -m "description"
uv run alembic upgrade head
```

### Web Service Architecture

FastAPI 分层架构：`routers/` → `dependencies.py` → `services/` → `models/` + `schemas/`

- **main.py** — FastAPI 入口，CORS、路由注册、health check
- **config.py** — pydantic-settings，从 `.env` 读取配置
- **database.py** — SQLAlchemy Base、engine、get_db
- **dependencies.py** — FastAPI 依赖注入（JWT 认证、SMS 服务）
- **models/** — User、CreditAccount、RechargePackage、PaymentOrder、CreditTransaction ORM 模型
- **schemas/** — Pydantic 请求/响应模型：auth.py、credits.py、admin.py
- **services/** — 业务逻辑：token.py（JWT）、sms.py（验证码）、auth.py（登录注册）、credit.py（积分充值/消费/流水）、payment.py（支付抽象层 + 支付宝 + 订单管理）、admin.py（管理后台：套餐CRUD、用户管理、数据看板、配置）
- **routers/** — API 路由：auth.py（/api/auth/*）、credits.py（/api/credits/*）、admin.py（/api/admin/*）

### Web Frontend (from `web/frontend/` directory)

```bash
# 安装依赖
npm install

# 启动开发服务器
npm run dev

# 构建
npm run build
```

前端技术栈：React 19 + TypeScript + Ant Design + Zustand + Axios + Vite

### Database

默认 SQLite（开发用），生产环境 PostgreSQL。通过 `web/.env` 的 `DATABASE_URL` 配置。

```bash
# Docker 启动 PostgreSQL
docker compose up -d db
```

### API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/health | 健康检查 |
| POST | /api/auth/sms/send | 发送验证码 |
| POST | /api/auth/login/phone | 手机号登录（自动注册） |
| POST | /api/auth/refresh | 刷新 token |
| GET | /api/auth/me | 当前用户信息 |
| GET | /api/credits/packages | 获取充值套餐列表 |
| POST | /api/credits/recharge | 创建充值订单 |
| GET | /api/credits/orders/{id} | 查询订单状态 |
| POST | /api/credits/payment/callback | 支付宝异步回调 |
| GET | /api/credits/transactions | 积分流水（分页） |
| GET | /api/credits/balance | 查询余额 |
| GET | /api/admin/dashboard | 管理数据看板（admin） |
| GET | /api/admin/packages | 套餐列表含已下架（admin） |
| POST | /api/admin/packages | 创建套餐（admin） |
| PUT | /api/admin/packages/{id} | 修改套餐（admin） |
| DELETE | /api/admin/packages/{id} | 删除套餐（admin） |
| GET | /api/admin/users | 用户列表分页搜索（admin） |
| PUT | /api/admin/users/{id}/credits | 调整积分（admin） |
| PUT | /api/admin/users/{id}/status | 禁用/启用用户（admin） |
| GET | /api/admin/config | 获取积分配置（admin） |
| PUT | /api/admin/config | 更新积分配置（admin） |

### Credits System

积分经济闭环：充值套餐 → 支付订单 → 积分到账 → 积分消费（P3 检测/改写）。

- **支付渠道**：`PaymentProvider` 抽象层，`AlipayProvider`（生产）/ `MockPaymentProvider`（开发，ALIPAY_APP_ID 为空时自动启用）
- **积分消费**：按 token × `CREDITS_PER_TOKEN` 扣减，余额不足抛 403
- **新人赠送**：`NEW_USER_BONUS_CREDITS` 配置，注册时自动发放
- **幂等**：支付回调先查订单状态，已 paid 不重复加积分

### Admin System

超管角色体系，通过 User 模型 `is_admin` 字段控制。超管通过管理后台配置套餐、积分价格、管理用户。

- **权限控制**：`require_admin` 依赖注入，所有 `/api/admin/*` 路由使用此依赖
- **超管创建**：手动在数据库 `UPDATE users SET is_admin = 1 WHERE phone = 'xxx'`
- **开发环境**：`DEV_TEST_PHONES` 指定测试手机号、`DEV_BYPASS_PHONE=true` 跳过验证码

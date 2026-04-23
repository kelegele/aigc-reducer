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

## Coding Standards

**规则生成机制**：排查到的一切编码问题（bug、遗漏、不一致、UX 缺陷），修复后都必须提炼为一条通用规范追加到下方对应章节。不仅是修复当前代码，更要防止同类问题再发生。

## Frontend Coding Rules

### 错误处理规范

所有涉及 API 调用的用户操作（按钮点击、表单提交）**必须**使用 try-catch，并在 catch 中提取后端 `response.data.detail` 展示给用户。禁止使用泛泛的默认错误信息。

```typescript
try {
  await someApiCall();
  message.success("操作成功");
} catch (err: unknown) {
  const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
  if (detail) message.error(detail);
}
```

**原因**：后端所有错误都通过 `{ "detail": "具体原因" }` 返回。前端吞掉 detail 显示"操作失败"会让用户无法排查问题，也让开发调试困难。

### 前后端字段一致性

新增后端 schema 字段时，**必须同步**：
1. 后端 `schemas/` 中的 Pydantic model
2. 后端 `services/` 中构造 response 的代码（所有 return 该 schema 的地方）
3. 前端 `api/` 中的 TypeScript interface
4. 前端页面中使用该字段的代码

**检查方法**：添加字段后 grep 后端所有 `UserResponse(`、`ConfigResponse(` 等构造调用，确保新字段被赋值。

### 金额展示

后端统一用**分**（int）存储和传输。前端展示时转换为**元**（÷100），输入时转换回分（×100）。禁止在界面上直接显示"分"。

### 数据加载

所有页面加载数据（useEffect 中调 API）都要处理失败情况：
- `.then().catch(() => {})` — 静默失败（统计数据等非关键数据）
- try-catch + message.error — 关键操作失败必须提示用户

### UTC 时间显示

后端返回 naive UTC datetime（无时区标记）。前端显示时间时必须追加 `"Z"` 再解析：

```typescript
new Date(item.created_at + "Z").toLocaleString("zh-CN")
```

**原因**：不加 `"Z"` 时 `new Date()` 按本地时区解析，导致显示时间偏移（如 UTC+8 环境下差 8 小时）。

### Toast/Modal 主题适配

所有 `message.xxx()` 和 `Modal.confirm()` **必须**使用 `App.useApp()` hook 获取实例，禁止直接使用 antd 静态方法。静态方法不继承 `ConfigProvider` 的主题上下文，导致深浅色切换时 Toast/弹窗样式不跟随。

```typescript
// 正确
import { App as AntApp } from "antd";
const { message, modal } = AntApp.useApp();

// 错误 — 不会跟随主题
import { message, Modal } from "antd";
```

**前提**：`App.tsx` 已用 `<AntApp>` 包裹路由，所有子组件均可使用此 hook。

### 设计规范

- `DESIGN.md` 为全站设计规范，所有页面（包括 Landing、Login、Dashboard、Admin）必须遵守其中的配色、字体、间距体系
- 所有页面必须同时适配深色和浅色模式，禁止硬编码颜色值（如 `#00d992`、`#f50`）
- 使用 `theme.useToken()` 获取主题 token（`token.colorPrimary`、`token.colorSuccess`、`token.colorError` 等）

### 首页 SEO/GEO 规范

Landing 页面（`/`）是面向搜索引擎和 AI 概览的公开页面，必须遵守 SEO 和 GEO 最佳实践：
- 语义化 HTML（h1/h2/h3 层级、section 划分）
- 完整的 meta 信息（title、description、keywords）
- 结构化内容（产品服务描述准确、简洁）
- 页脚信息真实、专业（联系方式、版权声明）

## Backend Coding Rules

### 事务原子性

多个相关的数据库写操作（如更新订单状态 + 积分充值）**必须**在同一事务中完成。禁止在关联操作之间调用 `db.commit()`，应使用 `db.flush()` 将变更推到事务内，由最后一个操作统一提交。

**原因**：`handle_payment_callback` 在 `credit_service.recharge()` 之前 `db.commit()` 提交了订单状态。当 recharge 因 NOT NULL 约束失败时，订单已标记 paid 但积分未到账，导致数据不一致。

### Migration 添加 NOT NULL 列

给已有数据的表添加 NOT NULL 列时，迁移脚本必须分三步：

```python
# 1. 先加列为 nullable
op.add_column('table', sa.Column('col', sa.String(64), nullable=True))
# 2. 回填已有数据
op.execute("UPDATE table SET col = ... WHERE col IS NULL")
# 3. 设为 NOT NULL + unique
op.alter_column('table', 'col', nullable=False)
op.create_unique_constraint(None, 'table', ['col'])
```

**原因**：直接加 NOT NULL 列时，已有行的 null 值违反约束导致迁移失败。

### 关联保护逻辑要区分状态

删除有关联数据的记录时，保护逻辑要考虑关联记录的状态。未完成的关联（如 pending 订单）不应阻止父记录删除；只有已完成的关联（如 paid 订单）才需要保护。

**原因**：P2 测试时创建了一条 pending 订单关联了套餐#1，导致套餐无法删除。实际上 pending 订单对业务无意义，不应阻止套餐下架或删除。

### 测试环境隔离

`conftest.py` 已有 `autouse` fixture 确保 `DEV_BYPASS_PHONE=False` 和 `DEV_TEST_PHONES=""`。新增涉及 dev-only 逻辑（如短信 bypass、权限提升）的代码时，**必须**在 `conftest.py` 同步 patch，防止 `.env` 开发配置干扰测试。

**原因**：`.env` 设置 `DEV_BYPASS_PHONE=true` 后，SMS 测试全部失败 — `verify()` 跳过了验证码校验逻辑，导致错误码、过期码、不存在的手机号全部通过验证。

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
| GET | /api/credits/orders | 用户订单列表（分页、状态筛选） |
| GET | /api/credits/orders/{id} | 查询订单状态 |
| GET | /api/credits/orders/{id}/detail | 订单详情（含关联流水） |
| POST | /api/credits/orders/{id}/repay | 待支付订单重新获取支付链接 |
| POST | /api/credits/payment/callback | 支付宝异步回调 |
| GET | /api/credits/transactions | 积分流水（分页） |
| GET | /api/credits/balance | 查询余额 |
| GET | /api/admin/dashboard | 管理数据看板（admin） |
| GET | /api/admin/packages | 套餐列表含已下架（admin） |
| POST | /api/admin/packages | 创建套餐（admin） |
| PUT | /api/admin/packages/{id} | 修改套餐（admin） |
| DELETE | /api/admin/packages/{id} | 删除套餐（admin） |
| GET | /api/admin/orders | 全部订单列表（admin，分页、搜索、状态筛选） |
| GET | /api/admin/orders/{id} | 订单详情含用户信息（admin） |
| GET | /api/admin/users | 用户列表分页搜索（admin） |
| PUT | /api/admin/users/{id}/credits | 调整积分（admin） |
| PUT | /api/admin/users/{id}/status | 禁用/启用用户（admin） |
| GET | /api/admin/config | 获取积分配置（admin） |
| PUT | /api/admin/config | 更新积分配置（admin） |

### Credits System

积分经济闭环：充值套餐 → 支付订单 → 积分到账 → 积分消费（P3 检测/改写）。

- **支付渠道**：`PaymentProvider` 抽象层，`AlipayProvider`（生产）/ `MockPaymentProvider`（开发，ALIPAY_APP_ID 为空时自动启用）
- **支付确认**：主动查询（`query_trade`）为主，异步回调为辅。前端双重机制：新 tab 支付 + 弹窗轮询 + return URL 回跳检测
- **积分消费**：按 token × `CREDITS_PER_TOKEN` 扣减，余额不足抛 403
- **新人赠送**：`NEW_USER_BONUS_CREDITS` 配置，注册时自动发放
- **幂等**：支付回调先查订单状态，已 paid 不重复加积分

### Admin System

超管角色体系，通过 User 模型 `is_admin` 字段控制。超管通过管理后台配置套餐、积分价格、管理用户。

- **权限控制**：`require_admin` 依赖注入，所有 `/api/admin/*` 路由使用此依赖
- **超管创建**：通过 `ADMIN_PHONE` 环境变量指定手机号，登录时自动提升为超管
- **开发环境**：`DEV_TEST_PHONES` 指定测试手机号、`DEV_BYPASS_PHONE=true` 跳过验证码

### Tech Debt

（暂无）

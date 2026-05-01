# AIGC Reducer

降低学术论文 AIGC 查重率的工具，支持 CLI 和 Web 两种使用方式。

双引擎检测（规则引擎 + LLM 反查）+ 5 种 AI 改写风格，有效降低知网、GoCheck 等平台的 AI 查重率。

## 项目结构

```
aigc-reducer/
├── core/                # 共享引擎（aigc-reducer-core 包）
│   └── src/aigc_reducer_core/
│       ├── detector.py  #   检测编排（rules + llm 双模式）
│       ├── rewriter.py  #   改写编排（5 风格 × 2 档改写）
│       ├── parser.py    #   文档解析（.docx / .doc / .pdf / .md）
│       ├── llm_client.py#   LLM 统一客户端（LiteLLM）
│       ├── detectors/   #   5 维规则检测器
│       └── styles/      #   5 种改写风格
├── cli/                 # CLI 工具（Python，交互式终端）
├── web/                 # Web 服务
│   ├── src/aigc_web/    #   FastAPI 后端（分层架构）
│   ├── frontend/        #   React 19 SPA（TypeScript + Ant Design 6）
│   ├── alembic/         #   数据库迁移
│   └── tests/           #   后端测试
├── docs/superpowers/    # 设计文档和实现计划
└── docker-compose.yml   # Docker 部署（PostgreSQL + API）
```

## 快速开始

```bash
# 1. 启动 PostgreSQL
docker compose up -d db

# 2. 安装依赖 & 运行迁移
cd web && uv sync
uv run alembic upgrade head

# 3. 启动后端（端口 9000）
uv run uvicorn aigc_web.main:app --port 9000

# 4. 启动前端（另一个终端，端口 5173）
cd web/frontend && npm install && npm run dev
```

访问 http://localhost:5173。Swagger 文档：http://localhost:9000/docs。

## CLI 工具

交互式 CLI，逐步引导完成检测 → 改写 → 导出。

```bash
cd cli && uv sync
uv run aigc-reduce
```

- 输入文件支持 `.docx` / `.doc` / `.pdf` / `.md`
- 双模式检测：规则引擎（5 维特征，免费）或 LLM 反查（大模型模拟商业检测平台，消耗积分）
- 5 种改写风格：学术人文化、口语化、文言文化、中英混杂化、粗犷草稿风
- 交互式逐段确认，每个高风险段落提供 A/B 两档改写方案
- 输出文件：`*_reduced.md`（改写全文）、`*_diff.md`（差异对比）、`*_revision_report.md`（整改建议）

详细用法见 [cli/README.md](cli/README.md)。

## Web 服务

手机号验证码登录 + 积分账户 + 管理员后台。

### 6 步检测流水线

```
上传文档 → 解析段落 → 检测风险 → (可选)全量语义重构 → 逐段改写确认 → 生成最终文档
```

- **检测模式**：规则引擎（免费）或 LLM 反查（消耗积分）
- **改写风格**：5 种风格，每种提供 aggressive / conservative 两档
- **SSE 流式推送**：检测/改写进度实时推送到前端
- **取消任务**：进行中的任务可随时停止
- **并发控制**：每个用户同时只能有一个进行中的任务，新建时弹窗引导查看已有任务

### 积分系统

积分充值 → 支付（支付宝）→ 消费（检测/改写按 token 扣减）→ 流水记录。

- `CREDITS_PER_1K_TOKENS` 汇率在管理后台动态配置，持久化到数据库，重启不丢失
- 新人注册赠送积分（`NEW_USER_BONUS_CREDITS`）
- 余额不足时操作被拒绝（403）
- 积分流水支持按类型筛选、按任务 ID 搜索

### 管理后台

超管（ADMIN_PHONE 配置）可访问管理后台（`/admin/*`）：

- **数据看板**：用户数、订单数、营收统计
- **套餐管理**：创建 / 修改 / 删除充值套餐
- **订单管理**：查看全部订单、按状态筛选
- **用户管理**：用户列表、积分调整、禁用/启用
- **流水管理**：全部积分流水、按类型/手机号搜索
- **内容管理**：查看所有用户的检测记录
- **积分配置**：动态调整 CPT 汇率和新人赠送积分

### API 端点

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/health | 健康检查 |
| **认证** | | |
| POST | /api/auth/sms/send | 发送验证码 |
| POST | /api/auth/login/phone | 手机号登录（自动注册） |
| POST | /api/auth/refresh | 刷新 token |
| GET | /api/auth/me | 当前用户信息 |
| PUT | /api/auth/me/profile | 修改昵称/头像 |
| **积分** | | |
| GET | /api/credits/packages | 充值套餐列表 |
| POST | /api/credits/recharge | 创建充值订单 |
| GET | /api/credits/orders | 用户订单列表 |
| POST | /api/credits/payment/callback | 支付宝异步回调 |
| GET | /api/credits/transactions | 积分流水（分页） |
| **检测** | | |
| POST | /api/reduce/tasks | 创建任务（multipart: file 或 text + 检测模式 + 风格） |
| GET | /api/reduce/tasks | 任务列表（分页、状态筛选、关键词搜索） |
| GET | /api/reduce/tasks/{id} | 任务详情（含所有段落） |
| POST | /api/reduce/tasks/{id}/estimate | 预估积分消耗 |
| POST | /api/reduce/tasks/{id}/detect | 开始检测（SSE 流式） |
| POST | /api/reduce/tasks/{id}/rewrite | 开始改写（SSE 流式） |
| POST | /api/reduce/tasks/{id}/reconstruct | 全量语义重构（SSE 流式） |
| PUT | /api/reduce/tasks/{id}/paragraphs/{index} | 确认段落选择 |
| POST | /api/reduce/tasks/{id}/finalize | 生成最终文档 |
| POST | /api/reduce/tasks/{id}/cancel | 取消任务 |
| GET | /api/reduce/tasks/{id}/export | 导出结果（markdown / docx） |
| GET | /api/reduce/stats | 用户统计数据 |
| **管理后台** | | |
| GET | /api/admin/dashboard | 数据看板 |
| GET/POST | /api/admin/packages | 套餐列表 / 创建 |
| PUT/DELETE | /api/admin/packages/{id} | 修改 / 删除套餐 |
| GET | /api/admin/orders | 全部订单列表 |
| GET | /api/admin/users | 用户列表 |
| PUT | /api/admin/users/{id}/credits | 调整积分 |
| PUT | /api/admin/users/{id}/status | 禁用/启用用户 |
| GET | /api/admin/transactions | 全部积分流水 |
| GET/PUT | /api/admin/config | 获取 / 更新积分配置 |
| GET | /api/admin/tasks | 全部检测记录（含用户信息） |

## 技术栈

| 层 | 技术 |
|---|---|
| 共享引擎 | Python 3.12 + LiteLLM |
| Web 后端 | FastAPI + SQLAlchemy 2.0 + Alembic + JWT + APScheduler |
| Web 前端 | React 19 + TypeScript + Ant Design 6 + Zustand + Axios + Vite |
| 数据库 | PostgreSQL |
| 支付 | 支付宝（python-alipay-sdk），开发环境自动切换到 Mock |
| 部署 | Docker Compose（PostgreSQL + API 服务） |

## 开发

```bash
# CLI 测试
cd cli && uv run pytest tests/ -v

# Web 后端测试
cd web && uv run pytest tests/ -v

# Web 前端类型检查
cd web/frontend && npx tsc --noEmit

# Web 前端构建
cd web/frontend && npm run build
```

### 编码规范

项目维护了严格的编码规范体系，见 [CLAUDE.md](CLAUDE.md)。关键规则包括：

- 枚举常量禁止硬编码字符串（数据层英文 key，展示层中文映射）
- 下拉筛选框必须用 `allowClear` + `placeholder`，禁止"全部"作为单选选项
- 每个用户同时只能有一个进行中的任务
- 状态筛选必须覆盖所有终端状态
- 端口配置必须走环境变量，切换分支后必须重启后端进程

### 7 大风险维度

| 维度 | 检测方法 | 权重 |
|------|---------|------|
| 困惑度（Perplexity） | 用词标准化程度 | 20% |
| 突发性（Burstiness） | 句式长度方差 | 20% |
| 连接词（Connectors） | 模板化连接词频率 | 20% |
| 认知特征（Cognitive） | 批判性思维标记 | 20% |
| 语义指纹（Semantic Fingerprint） | AI 论证结构模式 | 20% |

综合分 ≥10% 为中风险，≥30% 为中高风险，≥60% 为高风险。

### 5 种改写风格

| 风格 | 定位 |
|------|------|
| 学术人文化（推荐） | 保留学术严谨性，融入自然人类写作节奏 |
| 口语化 | 书面语转自然接地气的表达 |
| 文言文化 | 融入文言表达，打破现代白话 AI 模式 |
| 中英混杂化 | 适度插入英文术语，模拟双语学术写作 |
| 粗犷草稿风 | 模拟手动初稿的粗放感，句式不规则 |

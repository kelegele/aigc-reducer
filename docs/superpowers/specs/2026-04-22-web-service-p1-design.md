# P1: Web 服务骨架 — 设计文档

## Context

AIGC Reducer 现有 CLI 工具需要转为 Web 服务，支持用户登录、充值积分、论文检测按 Token 扣费的完整商业流程。整体项目拆分为 4 个子项目（P1-P4），本文档为 P1（Web 服务骨架）的设计。

P1 目标：搭建 Web 服务基础架构，实现用户认证（手机号+验证码）和积分账户系统，为后续支付（P2）、论文检测核心 API（P3）、历史记录（P4）打下基础。

## 项目结构

在现有 monorepo 中新增 `web/` 目录，与 `cli/` 并列：

```
aigc-reducer/
├── cli/                        # 现有 CLI 工具（不动）
├── web/                        # 新增 Web 服务
│   ├── pyproject.toml          # Web 后端依赖
│   ├── .env.example
│   ├── alembic.ini
│   ├── alembic/
│   │   ├── env.py
│   │   └── versions/
│   ├── src/
│   │   └── aigc_web/
│   │       ├── __init__.py
│   │       ├── main.py                # FastAPI app 入口
│   │       ├── config.py              # 配置管理
│   │       ├── database.py            # SQLAlchemy 引擎和 Session
│   │       ├── models/                # ORM 模型
│   │       │   ├── __init__.py
│   │       │   ├── user.py            # User 模型
│   │       │   └── credit_account.py  # CreditAccount 模型
│   │       ├── schemas/               # Pydantic 请求/响应模型
│   │       │   ├── __init__.py
│   │       │   └── auth.py
│   │       ├── routers/               # API 路由
│   │       │   ├── __init__.py
│   │       │   └── auth.py            # 注册/登录/刷新
│   │       ├── services/              # 业务逻辑
│   │       │   ├── __init__.py
│   │       │   └── auth.py
│   │       └── dependencies.py        # 公共依赖（get_db, get_current_user）
│   ├── frontend/                      # React 前端
│   │   ├── package.json
│   │   ├── tsconfig.json
│   │   ├── vite.config.ts
│   │   └── src/
│   │       ├── App.tsx
│   │       ├── main.tsx
│   │       ├── api/                   # API 调用封装
│   │       │   ├── client.ts          # Axios 实例 + 拦截器
│   │       │   └── auth.ts            # 认证相关 API
│   │       ├── stores/                # Zustand 状态管理
│   │       │   └── auth.ts
│   │       ├── pages/
│   │       │   ├── Login.tsx
│   │       │   ├── Dashboard.tsx
│   │       │   ├── Credits.tsx
│   │       │   ├── History.tsx
│   │       │   └── Settings.tsx
│   │       ├── components/
│   │       │   ├── Layout.tsx         # 全局布局（导航栏+内容区）
│   │       │   └── ProtectedRoute.tsx # 路由守卫
│   │       └── styles/
│   │           └── global.css
│   └── tests/
│       └── test_auth.py
└── docs/superpowers/
```

**关键决策：**
- `web/` 与 `cli/` 独立，各自有 `pyproject.toml`
- Web 后端通过 `import` 引用 `cli/src/aigc_reducer/` 的核心模块（P3 阶段使用）
- 前端嵌入 `web/frontend/`，开发时 Vite dev server 代理到 FastAPI

## 数据库模型

### User 表

```python
class User(Base):
    __tablename__ = "users"

    id: Mapped[int]                     # 主键，自增
    phone: Mapped[str]                  # 手机号，唯一，主登录标识
    nickname: Mapped[str]               # 昵称（可修改）
    avatar_url: Mapped[str | None]      # 头像（微信登录可同步）
    wechat_openid: Mapped[str | None]   # 微信 OpenID（预留，P1 不实现）
    wechat_unionid: Mapped[str | None]  # 微信 UnionID（预留）
    phone_verified: Mapped[bool]        # 手机号是否已验证，默认 True
    is_active: Mapped[bool]             # 是否激活，默认 True
    is_admin: Mapped[bool]              # 管理员标记，默认 False
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]
```

### CreditAccount 表

```python
class CreditAccount(Base):
    __tablename__ = "credit_accounts"

    id: Mapped[int]
    user_id: Mapped[int]                # 外键 -> users.id，唯一约束
    balance: Mapped[int]                # 当前积分余额，默认 0
    total_recharged: Mapped[int]        # 累计充值积分，默认 0
    total_consumed: Mapped[int]         # 累计消耗积分，默认 0
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]
```

**设计说明：**
- 积分账户独立于用户表，方便后续扩展（冻结、积分流水等）
- User 创建时自动创建关联的 CreditAccount（数据库触发或服务层保证）
- 微信字段预留但不实现，P1 阶段可为 NULL

## 用户认证系统

### 登录方式

**P1 实现：手机号 + 短信验证码**

1. `POST /api/auth/sms/send` — 发送短信验证码
   - 请求：`{ "phone": "13800138000" }`
   - 限制：同一手机号 60 秒内只能发一次
   - 验证码 6 位数字，5 分钟有效
   - 存储在 Redis（或简单场景用内存 dict + TTL）

2. `POST /api/auth/login/phone` — 手机号验证码登录
   - 请求：`{ "phone": "13800138000", "code": "123456" }`
   - 手机号不存在则自动注册（首次登录即注册）
   - 返回：`{ "access_token": "...", "refresh_token": "...", "user": {...} }`

**预留（后续阶段）：微信扫码登录**

- 微信扫码后若已绑定手机号 → 直接登录
- 若未绑定 → 要求绑定手机号（走短信验证码）
- 数据库中 `wechat_openid` / `wechat_unionid` 字段已预留

### JWT Token 策略

| Token | 有效期 | 用途 |
|-------|--------|------|
| access_token | 30 分钟 | API 调用凭证 |
| refresh_token | 7 天 | 刷新 access_token |

- 使用 `python-jose` 生成和验证 JWT
- Token payload: `{ "sub": user_id, "type": "access"|"refresh", "exp": ... }`

### API 接口

| 方法 | 路径 | 认证 | 说明 |
|------|------|------|------|
| POST | `/api/auth/sms/send` | 无 | 发送短信验证码 |
| POST | `/api/auth/login/phone` | 无 | 手机号验证码登录 |
| POST | `/api/auth/refresh` | refresh_token | 刷新 access_token |
| GET | `/api/auth/me` | access_token | 获取当前用户信息（含积分余额） |

### 认证依赖注入

```python
# dependencies.py
async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    """从 JWT 解析用户，Token 无效或过期抛 401"""

async def get_current_active_user(user: User = Depends(get_current_user)) -> User:
    """确保用户处于激活状态"""
```

## 前端设计

### 技术选型

| 组件 | 选择 | 理由 |
|------|------|------|
| 构建工具 | Vite | 快速 HMR，TypeScript 支持好 |
| UI 框架 | Ant Design 5 | 中文文档完善，表单/反馈组件齐全，支持响应式 |
| HTTP 客户端 | Axios | 拦截器方便统一处理 Token |
| 路由 | React Router v6 | 标准选择 |
| 状态管理 | Zustand | 轻量简洁 |
| CSS | Ant Design Token + CSS Modules | 主题定制 + 局部样式隔离 |
| 移动端 | Ant Design Grid + media queries | 桌面端优先，手机能看 |

### 页面路由

| 路径 | 页面 | 认证 |
|------|------|------|
| `/login` | 手机号+验证码登录 | 无 |
| `/dashboard` | 仪表盘（积分余额、快捷入口） | 需要 |
| `/credits` | 积分页面（余额+流水） | 需要 |
| `/history` | 检测历史 | 需要 |
| `/settings` | 个人设置（昵称、头像） | 需要 |

### 布局结构

```
桌面端：
┌─────────────────────────────────────┐
│  导航栏 (Logo | 功能菜单 | 用户头像) │
├─────────────────────────────────────┤
│         主内容区域                   │
│         (根据路由渲染)               │
└─────────────────────────────────────┘

移动端：
┌───────────────┐
│  Logo  ☰菜单  │
├───────────────┤
│               │
│  主内容区域    │
│               │
└───────────────┘
（复杂表格/对比组件在移动端简化展示）
```

### 前端认证流程

1. 登录成功后，tokens 存入 localStorage
2. Axios 拦截器在每个请求附加 `Authorization: Bearer <token>`
3. 收到 401 → 自动尝试 refresh_token 刷新
4. 刷新也失败 → 清除 tokens，跳转 `/login`
5. 路由守卫 `ProtectedRoute`：未登录访问受保护页面 → 跳转登录

## 配置管理

```python
# config.py
class Settings(BaseSettings):
    # 数据库
    DATABASE_URL: str                      # PostgreSQL 连接串

    # JWT
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # 短信服务
    SMS_PROVIDER: str                      # "aliyun" | "tencent"
    SMS_ACCESS_KEY: str
    SMS_ACCESS_SECRET: str
    SMS_SIGN_NAME: str
    SMS_TEMPLATE_CODE: str

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:5173"]

    # LLM（复用 cli 配置，P3 阶段使用）
    LLM_MODEL: str = ""
    LLM_API_KEY: str = ""
    LLM_BASE_URL: str | None = None

    class Config:
        env_file = ".env"
```

## 错误处理

| 场景 | HTTP 状态 | 处理方式 |
|------|----------|---------|
| 验证码错误/过期 | 400 | 返回明确错误信息 |
| Token 过期 | 401 | 前端自动刷新 |
| Token 无效 | 401 | 跳转登录 |
| 积分不足 | 403 | 提示充值 |
| 参数校验失败 | 422 | FastAPI + Pydantic 自动处理 |
| 服务端异常 | 500 | 统一错误响应，记录日志 |

## 后端依赖

```toml
# web/pyproject.toml [project.dependencies]
fastapi >= 0.110
uvicorn[standard] >= 0.29
sqlalchemy >= 2.0
asyncpg >= 0.29                # PostgreSQL async driver
alembic >= 1.13
python-jose[cryptography] >= 3.3
passlib[bcrypt] >= 1.7
pydantic-settings >= 2.0
httpx >= 0.27                  # 短信 API 调用
redis >= 5.0                   # 验证码存储（可选）
```

## 开发流程

```bash
# 后端
cd web
uv sync
uv run uvicorn aigc_web.main:app --reload --port 8000

# 数据库迁移
uv run alembic upgrade head

# 前端
cd web/frontend
npm install
npm run dev                    # 默认 http://localhost:5173，代理到 8000

# 测试
cd web
uv run pytest tests/
```

## P1 不包含的内容

以下内容在后续子项目中实现：

- **P2**：微信支付/支付宝集成、充值套餐、积分消费引擎
- **P3**：论文检测/改写 API、SSE 进度推送、完整交互前端页面
- **P4**：检测历史、结果回看、管理后台
- 微信扫码登录（数据库字段已预留）
- 生产部署和 CI/CD

## 验证方式

P1 完成后应能验证：

1. **后端**：`uv run uvicorn` 启动无报错，访问 `http://localhost:8000/docs` 看到 Swagger UI
2. **注册登录**：通过 Swagger 或前端发送验证码 → 登录 → 获取 access_token
3. **Token 认证**：用 access_token 调用 `GET /api/auth/me` 返回用户信息
4. **Token 刷新**：access_token 过期后用 refresh_token 刷新成功
5. **前端**：`npm run dev` 启动，登录页正常显示，登录后跳转 Dashboard
6. **积分显示**：Dashboard 显示积分余额（初始为 0）
7. **响应式**：手机尺寸下页面布局可读

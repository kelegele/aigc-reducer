# P1: Web 服务骨架 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 搭建 FastAPI Web 服务骨架，实现手机号验证码登录和积分账户系统

**Architecture:** FastAPI + SQLAlchemy 2.0 + Alembic 后端，Vite + React + Ant Design 前端。后端用同步 SQLAlchemy 操作 PostgreSQL，前端通过 Axios 调用 API，JWT 认证保护路由。

**Tech Stack:** FastAPI, SQLAlchemy 2.0, Alembic, python-jose, passlib, psycopg2-binary, React 18, TypeScript, Ant Design 5, Zustand, Axios, Vite

---

## File Structure

```
web/
├── pyproject.toml
├── .env.example
├── .gitignore
├── alembic.ini
├── alembic/
│   ├── env.py
│   └── versions/                    # 自动生成
├── src/
│   └── aigc_web/
│       ├── __init__.py              # 版本号
│       ├── main.py                  # FastAPI app 入口、CORS、路由注册
│       ├── config.py                # pydantic-settings 配置
│       ├── database.py              # SQLAlchemy Base、engine、get_db
│       ├── dependencies.py          # get_current_user、get_verification_service
│       ├── models/
│       │   ├── __init__.py          # 导出 User、CreditAccount
│       │   ├── user.py              # User ORM 模型
│       │   └── credit_account.py    # CreditAccount ORM 模型
│       ├── schemas/
│       │   ├── __init__.py
│       │   └── auth.py              # 请求/响应 Pydantic 模型
│       ├── services/
│       │   ├── __init__.py
│       │   ├── token.py             # JWT 创建/验证
│       │   ├── sms.py               # 验证码生成、存储、发送、校验
│       │   └── auth.py              # 登录/注册业务逻辑
│       └── routers/
│           ├── __init__.py
│           └── auth.py              # /api/auth/* 路由
├── frontend/
│   ├── package.json
│   ├── tsconfig.json
│   ├── tsconfig.app.json
│   ├── tsconfig.node.json
│   ├── vite.config.ts
│   ├── index.html
│   └── src/
│       ├── main.tsx                 # React 入口
│       ├── App.tsx                  # 路由定义
│       ├── vite-env.d.ts
│       ├── api/
│       │   ├── client.ts            # Axios 实例 + 拦截器
│       │   └── auth.ts              # 认证 API 函数
│       ├── stores/
│       │   └── auth.ts              # Zustand auth store
│       ├── pages/
│       │   ├── Login.tsx            # 手机号+验证码登录页
│       │   ├── Dashboard.tsx        # 仪表盘（积分余额）
│       │   ├── Credits.tsx          # 积分页面（P2 完善）
│       │   ├── History.tsx          # 检测历史（P3 完善）
│       │   └── Settings.tsx         # 个人设置
│       └── components/
│           ├── AppLayout.tsx        # 全局布局（导航栏+内容）
│           └── ProtectedRoute.tsx   # 路由守卫
└── tests/
    ├── __init__.py
    ├── conftest.py                  # 测试数据库、fixtures
    ├── test_models.py               # 模型测试
    ├── test_token.py                # JWT 工具测试
    ├── test_sms.py                  # 验证码服务测试
    ├── test_auth_service.py         # 认证业务逻辑测试
    └── test_auth_router.py          # API 集成测试
```

---

### Task 1: Web 项目脚手架

**Files:**
- Create: `web/pyproject.toml`
- Create: `web/.env.example`
- Create: `web/.gitignore`
- Create: `web/src/aigc_web/__init__.py`
- Create: `web/tests/__init__.py`

- [ ] **Step 1: 创建目录结构**

```bash
mkdir -p web/src/aigc_web/{models,schemas,services,routers}
mkdir -p web/tests
```

- [ ] **Step 2: 创建 pyproject.toml**

```toml
# web/pyproject.toml
[project]
name = "aigc-web"
version = "0.1.0"
description = "AIGC Reducer Web 服务"
requires-python = ">=3.10"
dependencies = [
    "fastapi>=0.110",
    "uvicorn[standard]>=0.29",
    "sqlalchemy>=2.0",
    "psycopg2-binary>=2.9",
    "alembic>=1.13",
    "python-jose[cryptography]>=3.3",
    "passlib[bcrypt]>=1.7",
    "pydantic-settings>=2.0",
    "httpx>=0.27",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-cov>=4.0.0",
]

[build-system]
requires = ["setuptools>=68.0"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
```

- [ ] **Step 3: 创建 .env.example**

```bash
# web/.env.example
# 数据库
DATABASE_URL=postgresql://user:password@localhost:5432/aigc_reducer

# JWT
JWT_SECRET_KEY=change-me-to-a-random-string-in-production
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# 短信服务
SMS_PROVIDER=dev
# SMS_ACCESS_KEY=
# SMS_ACCESS_SECRET=
# SMS_SIGN_NAME=
# SMS_TEMPLATE_CODE=

# CORS
CORS_ORIGINS=["http://localhost:5173"]
```

- [ ] **Step 4: 创建 .gitignore**

```
# web/.gitignore
__pycache__/
*.py[cod]
*.egg-info/
dist/
.env
.venv/
output/
node_modules/
frontend/dist/
frontend/.vite/
*.db
```

- [ ] **Step 5: 创建 __init__.py 文件**

```python
# web/src/aigc_web/__init__.py
"""AIGC Reducer Web 服务"""

__version__ = "0.1.0"
```

```python
# web/tests/__init__.py
```

- [ ] **Step 6: 安装依赖并验证**

```bash
cd web
uv sync
uv run python -c "import fastapi; print(fastapi.__version__)"
```

Expected: 输出 FastAPI 版本号，无报错

- [ ] **Step 7: 提交**

```bash
git add web/
git commit -m "feat(web): scaffold web project with FastAPI dependencies"
```

---

### Task 2: 配置与数据库模块

**Files:**
- Create: `web/src/aigc_web/config.py`
- Create: `web/src/aigc_web/database.py`

- [ ] **Step 1: 创建 config.py**

```python
# web/src/aigc_web/config.py
"""应用配置 — 从环境变量 / .env 文件读取。"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # 数据库
    DATABASE_URL: str = "sqlite:///./dev.db"

    # JWT
    JWT_SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # 短信服务（"dev" = 开发模式，验证码打印到控制台）
    SMS_PROVIDER: str = "dev"
    SMS_ACCESS_KEY: str = ""
    SMS_ACCESS_SECRET: str = ""
    SMS_SIGN_NAME: str = ""
    SMS_TEMPLATE_CODE: str = ""

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:5173"]

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
```

- [ ] **Step 2: 创建 database.py**

```python
# web/src/aigc_web/database.py
"""SQLAlchemy 引擎、Base 和 Session 工厂。"""

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from aigc_web.config import settings


class Base(DeclarativeBase):
    pass


engine = create_engine(settings.DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

- [ ] **Step 3: 验证模块可导入**

```bash
cd web
uv run python -c "from aigc_web.config import settings; print(settings.DATABASE_URL)"
uv run python -c "from aigc_web.database import Base; print(Base)"
```

Expected: 输出默认 DATABASE_URL 和 Base 类，无报错

- [ ] **Step 4: 提交**

```bash
git add web/src/aigc_web/config.py web/src/aigc_web/database.py
git commit -m "feat(web): add config and database modules"
```

---

### Task 3: User 模型

**Files:**
- Create: `web/src/aigc_web/models/__init__.py`
- Create: `web/src/aigc_web/models/user.py`

- [ ] **Step 1: 创建 user.py**

```python
# web/src/aigc_web/models/user.py
"""用户 ORM 模型。"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from aigc_web.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    phone: Mapped[str] = mapped_column(String(11), unique=True, index=True, nullable=False)
    nickname: Mapped[str] = mapped_column(String(50), nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    wechat_openid: Mapped[str | None] = mapped_column(String(100), nullable=True)
    wechat_unionid: Mapped[str | None] = mapped_column(String(100), nullable=True)
    phone_verified: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )
```

- [ ] **Step 2: 创建 models/__init__.py**

```python
# web/src/aigc_web/models/__init__.py
from aigc_web.models.user import User
from aigc_web.models.credit_account import CreditAccount

__all__ = ["User", "CreditAccount"]
```

注意：`credit_account` 尚未创建，此 import 暂时会报错。将在 Task 4 创建后解决。

- [ ] **Step 3: 提交**

```bash
git add web/src/aigc_web/models/
git commit -m "feat(web): add User ORM model"
```

---

### Task 4: CreditAccount 模型

**Files:**
- Create: `web/src/aigc_web/models/credit_account.py`
- Modify: `web/src/aigc_web/models/__init__.py`（已在 Task 3 中包含 CreditAccount import）

- [ ] **Step 1: 创建 credit_account.py**

```python
# web/src/aigc_web/models/credit_account.py
"""积分账户 ORM 模型。"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from aigc_web.database import Base


class CreditAccount(Base):
    __tablename__ = "credit_accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), unique=True, nullable=False
    )
    balance: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_recharged: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_consumed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship("User", backref="credit_account")
```

- [ ] **Step 2: 验证 models 可导入**

```bash
cd web
uv run python -c "from aigc_web.models import User, CreditAccount; print('OK')"
```

Expected: 输出 `OK`

- [ ] **Step 3: 提交**

```bash
git add web/src/aigc_web/models/credit_account.py
git commit -m "feat(web): add CreditAccount ORM model"
```

---

### Task 5: 模型测试 + Alembic 迁移

**Files:**
- Create: `web/tests/conftest.py`
- Create: `web/tests/test_models.py`
- Create: `web/alembic.ini`
- Create: `web/alembic/env.py`
- Create: `web/alembic/script.py.mako`

- [ ] **Step 1: 创建 conftest.py — 测试数据库和公共 fixtures**

```python
# web/tests/conftest.py
"""测试配置 — 使用 SQLite 内存数据库。"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from aigc_web.database import Base, get_db


@pytest.fixture
def db_engine():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session(db_engine):
    Session = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    session = Session()
    yield session
    session.close()
```

- [ ] **Step 2: 创建 test_models.py**

```python
# web/tests/test_models.py
"""ORM 模型单元测试。"""

from aigc_web.models.credit_account import CreditAccount
from aigc_web.models.user import User


def test_create_user(db_session):
    user = User(phone="13800138000", nickname="测试用户")
    db_session.add(user)
    db_session.commit()

    result = db_session.query(User).filter_by(phone="13800138000").one()
    assert result.id is not None
    assert result.phone == "13800138000"
    assert result.nickname == "测试用户"
    assert result.is_active is True
    assert result.is_admin is False
    assert result.phone_verified is True
    assert result.avatar_url is None
    assert result.wechat_openid is None


def test_create_credit_account(db_session):
    user = User(phone="13800138001", nickname="积分用户")
    db_session.add(user)
    db_session.commit()

    account = CreditAccount(user_id=user.id)
    db_session.add(account)
    db_session.commit()

    result = db_session.query(CreditAccount).filter_by(user_id=user.id).one()
    assert result.balance == 0
    assert result.total_recharged == 0
    assert result.total_consumed == 0


def test_user_credit_account_relationship(db_session):
    user = User(phone="13800138002", nickname="关系用户")
    db_session.add(user)
    db_session.commit()

    account = CreditAccount(user_id=user.id, balance=100)
    db_session.add(account)
    db_session.commit()

    db_session.refresh(user)
    assert user.credit_account.balance == 100


def test_user_phone_unique(db_session):
    user1 = User(phone="13800138003", nickname="用户A")
    db_session.add(user1)
    db_session.commit()

    user2 = User(phone="13800138003", nickname="用户B")
    db_session.add(user2)
    with pytest.raises(Exception):
        db_session.commit()
```

注意：test_phone_unique 需要 `import pytest`，在文件顶部加上。

更新：在文件顶部添加 `import pytest`。

- [ ] **Step 3: 运行模型测试**

```bash
cd web
uv run pytest tests/test_models.py -v
```

Expected: 4 个测试全部 PASS

- [ ] **Step 4: 初始化 Alembic**

```bash
cd web
uv run alembic init alembic
```

Expected: 生成 `alembic.ini` 和 `alembic/` 目录

- [ ] **Step 5: 配置 alembic.ini — 修改 sqlalchemy.url**

打开 `web/alembic.ini`，将 `sqlalchemy.url` 行改为：

```ini
sqlalchemy.url = postgresql://user:password@localhost:5432/aigc_reducer
```

注意：实际运行时由 `alembic/env.py` 从 Settings 读取，此处的值仅作占位。

- [ ] **Step 6: 配置 alembic/env.py**

```python
# web/alembic/env.py
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from alembic import context
from sqlalchemy import engine_from_config, pool

from aigc_web.config import settings
from aigc_web.database import Base
from aigc_web.models import credit_account, user  # noqa: F401

config = context.config
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

- [ ] **Step 7: 生成初始迁移（需要 PostgreSQL 运行）**

```bash
cd web
uv run alembic revision --autogenerate -m "create users and credit_accounts tables"
```

Expected: 生成迁移文件，包含 `users` 和 `credit_accounts` 两张表的 CREATE TABLE

- [ ] **Step 8: 应用迁移（需要 PostgreSQL 运行）**

```bash
cd web
uv run alembic upgrade head
```

Expected: 输出 `Running upgrade ... done`

- [ ] **Step 9: 提交**

```bash
git add web/tests/ web/alembic.ini web/alembic/
git commit -m "feat(web): add model tests and Alembic migration setup"
```

---

### Task 6: Auth Schemas — Pydantic 请求/响应模型

**Files:**
- Create: `web/src/aigc_web/schemas/__init__.py`
- Create: `web/src/aigc_web/schemas/auth.py`

- [ ] **Step 1: 创建 schemas/__init__.py**

```python
# web/src/aigc_web/schemas/__init__.py
```

- [ ] **Step 2: 创建 schemas/auth.py**

```python
# web/src/aigc_web/schemas/auth.py
"""认证相关的请求/响应模型。"""

from pydantic import BaseModel, Field


class SendSmsRequest(BaseModel):
    phone: str = Field(pattern=r"^1[3-9]\d{9}$", description="手机号")


class PhoneLoginRequest(BaseModel):
    phone: str = Field(pattern=r"^1[3-9]\d{9}$", description="手机号")
    code: str = Field(pattern=r"^\d{6}$", description="6 位验证码")


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str


class UserResponse(BaseModel):
    id: int
    phone: str
    nickname: str
    avatar_url: str | None
    is_active: bool
    credit_balance: int = 0

    model_config = {"from_attributes": True}


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    user: UserResponse


class MessageResponse(BaseModel):
    message: str
```

- [ ] **Step 3: 验证 schema 可导入**

```bash
cd web
uv run python -c "from aigc_web.schemas.auth import SendSmsRequest; print(SendSmsRequest(phone='13800138000'))"
```

Expected: 输出 `phone='13800138000'`

- [ ] **Step 4: 提交**

```bash
git add web/src/aigc_web/schemas/
git commit -m "feat(web): add auth Pydantic schemas"
```

---

### Task 7: JWT 工具 + 测试

**Files:**
- Create: `web/src/aigc_web/services/__init__.py`
- Create: `web/src/aigc_web/services/token.py`
- Create: `web/tests/test_token.py`

- [ ] **Step 1: 创建 services/__init__.py**

```python
# web/src/aigc_web/services/__init__.py
```

- [ ] **Step 2: 创建 services/token.py**

```python
# web/src/aigc_web/services/token.py
"""JWT Token 创建和验证。"""

from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

from aigc_web.config import settings


def create_access_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload = {"sub": str(user_id), "type": "access", "exp": expire}
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS
    )
    payload = {"sub": str(user_id), "type": "refresh", "exp": expire}
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str, expected_type: str) -> int:
    """解码 token 并返回 user_id。失败时抛 ValueError。"""
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
    except JWTError as e:
        raise ValueError(f"无效的 token: {e}") from e

    if payload.get("type") != expected_type:
        raise ValueError(f"token 类型错误，期望 {expected_type}")

    user_id_str = payload.get("sub")
    if not user_id_str:
        raise ValueError("token 缺少 sub 字段")

    return int(user_id_str)
```

- [ ] **Step 3: 创建 test_token.py**

```python
# web/tests/test_token.py
"""JWT token 创建和验证测试。"""

from aigc_web.services.token import create_access_token, create_refresh_token, decode_token


def test_create_and_decode_access_token():
    token = create_access_token(user_id=42)
    user_id = decode_token(token, expected_type="access")
    assert user_id == 42


def test_create_and_decode_refresh_token():
    token = create_refresh_token(user_id=42)
    user_id = decode_token(token, expected_type="refresh")
    assert user_id == 42


def test_decode_access_token_with_wrong_type():
    token = create_access_token(user_id=42)
    import pytest
    with pytest.raises(ValueError, match="token 类型错误"):
        decode_token(token, expected_type="refresh")


def test_decode_invalid_token():
    import pytest
    with pytest.raises(ValueError, match="无效的 token"):
        decode_token("invalid.token.here", expected_type="access")


def test_different_users_get_different_tokens():
    token1 = create_access_token(user_id=1)
    token2 = create_access_token(user_id=2)
    assert token1 != token2
    assert decode_token(token1, "access") == 1
    assert decode_token(token2, "access") == 2
```

- [ ] **Step 4: 运行测试**

```bash
cd web
uv run pytest tests/test_token.py -v
```

Expected: 5 个测试全部 PASS

- [ ] **Step 5: 提交**

```bash
git add web/src/aigc_web/services/ web/tests/test_token.py
git commit -m "feat(web): add JWT token creation and verification"
```

---

### Task 8: 验证码服务 + 测试

**Files:**
- Create: `web/src/aigc_web/services/sms.py`
- Create: `web/tests/test_sms.py`

- [ ] **Step 1: 创建 services/sms.py**

```python
# web/src/aigc_web/services/sms.py
"""验证码生成、存储、发送和校验。"""

import random
from datetime import datetime, timedelta, timezone

from aigc_web.config import settings


class _CodeEntry:
    __slots__ = ("code", "expires_at", "sent_at")

    def __init__(self, code: str, expires_at: datetime, sent_at: datetime):
        self.code = code
        self.expires_at = expires_at
        self.sent_at = sent_at


class VerificationCodeService:
    """验证码服务。内存存储，开发模式打印到控制台。"""

    CODE_LENGTH = 6
    CODE_TTL = timedelta(minutes=5)
    SEND_COOLDOWN = timedelta(seconds=60)

    def __init__(self) -> None:
        self._store: dict[str, _CodeEntry] = {}

    def send(self, phone: str) -> None:
        """生成验证码并发送到手机号。60 秒内不可重发。"""
        now = datetime.now(timezone.utc)
        existing = self._store.get(phone)
        if existing and now - existing.sent_at < self.SEND_COOLDOWN:
            remaining = 60 - int((now - existing.sent_at).total_seconds())
            raise ValueError(f"请 {remaining} 秒后再试")

        code = self._generate_code()
        self._store[phone] = _CodeEntry(
            code=code,
            expires_at=now + self.CODE_TTL,
            sent_at=now,
        )
        self._do_send(phone, code)

    def verify(self, phone: str, code: str) -> bool:
        """校验验证码。成功后清除，防止重复使用。"""
        entry = self._store.get(phone)
        if entry is None:
            return False

        now = datetime.now(timezone.utc)
        if now > entry.expires_at:
            del self._store[phone]
            return False

        if entry.code != code:
            return False

        del self._store[phone]
        return True

    def _generate_code(self) -> str:
        return "".join(random.choices("0123456789", k=self.CODE_LENGTH))

    def _do_send(self, phone: str, code: str) -> None:
        if settings.SMS_PROVIDER == "dev":
            print(f"[DEV SMS] 验证码 {code} -> {phone}")
            return
        # 生产环境：调用短信服务商 API（P2 实现）
        print(f"[SMS] 发送验证码到 {phone}（provider={settings.SMS_PROVIDER}）")
```

- [ ] **Step 2: 创建 test_sms.py**

```python
# web/tests/test_sms.py
"""验证码服务测试。"""

import pytest

from aigc_web.services.sms import VerificationCodeService


@pytest.fixture
def sms_service():
    return VerificationCodeService()


def test_send_creates_code(sms_service):
    sms_service.send("13800138000")
    # 验证码已存储，可通过 verify 校验


def test_verify_correct_code(sms_service):
    sms_service.send("13800138000")
    # 从 _store 中取出验证码（仅测试用）
    code = sms_service._store["13800138000"].code
    assert sms_service.verify("13800138000", code) is True


def test_verify_wrong_code(sms_service):
    sms_service.send("13800138000")
    assert sms_service.verify("13800138000", "000000") is False


def test_verify_expired_code(sms_service):
    sms_service.send("13800138000")
    code = sms_service._store["13800138000"].code
    # 模拟过期
    from datetime import datetime, timedelta, timezone
    sms_service._store["13800138000"].expires_at = datetime.now(timezone.utc) - timedelta(
        seconds=1
    )
    assert sms_service.verify("13800138000", code) is False


def test_verify_code_consumed_on_success(sms_service):
    sms_service.send("13800138000")
    code = sms_service._store["13800138000"].code
    assert sms_service.verify("13800138000", code) is True
    # 二次使用应失败
    assert sms_service.verify("13800138000", code) is False


def test_verify_nonexistent_phone(sms_service):
    assert sms_service.verify("13800138000", "123456") is False


def test_send_cooldown(sms_service):
    sms_service.send("13800138000")
    with pytest.raises(ValueError, match="秒后再试"):
        sms_service.send("13800138000")
```

- [ ] **Step 3: 运行测试**

```bash
cd web
uv run pytest tests/test_sms.py -v
```

Expected: 7 个测试全部 PASS

- [ ] **Step 4: 提交**

```bash
git add web/src/aigc_web/services/sms.py web/tests/test_sms.py
git commit -m "feat(web): add verification code service with in-memory storage"
```

---

### Task 9: Auth 业务逻辑 + 测试

**Files:**
- Create: `web/src/aigc_web/services/auth.py`
- Create: `web/tests/test_auth_service.py`

- [ ] **Step 1: 创建 services/auth.py**

```python
# web/src/aigc_web/services/auth.py
"""认证业务逻辑 — 登录（自动注册）、Token 刷新、用户查询。"""

from sqlalchemy.orm import Session

from aigc_web.models.credit_account import CreditAccount
from aigc_web.models.user import User
from aigc_web.schemas.auth import LoginResponse, UserResponse
from aigc_web.services.token import create_access_token, create_refresh_token, decode_token


def login_or_register(db: Session, phone: str) -> LoginResponse:
    """手机号验证码登录。用户不存在则自动创建。"""
    user = db.query(User).filter(User.phone == phone).first()
    if user is None:
        user = User(
            phone=phone,
            nickname=f"用户{phone[-4:]}",
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        # 创建积分账户
        account = CreditAccount(user_id=user.id)
        db.add(account)
        db.commit()

    # 获取积分余额
    account = db.query(CreditAccount).filter(CreditAccount.user_id == user.id).first()
    balance = account.balance if account else 0

    access_token = create_access_token(user.id)
    refresh_token = create_refresh_token(user.id)

    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserResponse(
            id=user.id,
            phone=user.phone,
            nickname=user.nickname,
            avatar_url=user.avatar_url,
            is_active=user.is_active,
            credit_balance=balance,
        ),
    )


def refresh_access_token(db: Session, refresh_token: str) -> str:
    """用 refresh_token 换取新 access_token。"""
    user_id = decode_token(refresh_token, expected_type="refresh")
    user = db.query(User).filter(User.id == user_id).first()
    if user is None or not user.is_active:
        raise ValueError("用户不存在或已禁用")
    return create_access_token(user.id)


def get_current_user(db: Session, token: str) -> User:
    """从 access_token 解析当前用户。"""
    user_id = decode_token(token, expected_type="access")
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise ValueError("用户不存在")
    if not user.is_active:
        raise ValueError("用户已禁用")
    return user


def get_user_response(db: Session, user: User) -> UserResponse:
    """构建包含积分余额的 UserResponse。"""
    account = db.query(CreditAccount).filter(CreditAccount.user_id == user.id).first()
    return UserResponse(
        id=user.id,
        phone=user.phone,
        nickname=user.nickname,
        avatar_url=user.avatar_url,
        is_active=user.is_active,
        credit_balance=account.balance if account else 0,
    )
```

- [ ] **Step 2: 创建 test_auth_service.py**

```python
# web/tests/test_auth_service.py
"""认证业务逻辑测试。"""

import pytest

from aigc_web.models.credit_account import CreditAccount
from aigc_web.models.user import User
from aigc_web.services import auth as auth_service
from aigc_web.services.token import create_access_token, create_refresh_token


def test_login_creates_new_user(db_session):
    result = auth_service.login_or_register(db_session, phone="13800138000")

    assert result.user.phone == "13800138000"
    assert result.user.nickname == "用户8000"
    assert result.user.is_active is True
    assert result.user.credit_balance == 0
    assert result.access_token
    assert result.refresh_token

    # 数据库中应有 1 个用户
    assert db_session.query(User).count() == 1


def test_login_returns_existing_user(db_session):
    user = User(phone="13800138000", nickname="已有用户")
    db_session.add(user)
    db_session.commit()

    result = auth_service.login_or_register(db_session, phone="13800138000")
    assert result.user.nickname == "已有用户"
    assert db_session.query(User).count() == 1


def test_login_creates_credit_account(db_session):
    auth_service.login_or_register(db_session, phone="13800138000")
    user = db_session.query(User).filter_by(phone="13800138000").one()
    account = db_session.query(CreditAccount).filter_by(user_id=user.id).one()
    assert account.balance == 0


def test_refresh_access_token(db_session):
    result = auth_service.login_or_register(db_session, phone="13800138000")
    new_access = auth_service.refresh_access_token(db_session, result.refresh_token)
    assert new_access != result.access_token


def test_refresh_with_invalid_token(db_session):
    with pytest.raises(ValueError):
        auth_service.refresh_access_token(db_session, "invalid.token.here")


def test_get_current_user(db_session):
    result = auth_service.login_or_register(db_session, phone="13800138000")
    user = auth_service.get_current_user(db_session, result.access_token)
    assert user.phone == "13800138000"


def test_get_current_user_inactive(db_session):
    user = User(phone="13800138000", nickname="禁用用户", is_active=False)
    db_session.add(user)
    db_session.commit()
    token = create_access_token(user.id)
    with pytest.raises(ValueError, match="已禁用"):
        auth_service.get_current_user(db_session, token)


def test_get_user_response(db_session):
    result = auth_service.login_or_register(db_session, phone="13800138000")
    user = auth_service.get_current_user(db_session, result.access_token)
    resp = auth_service.get_user_response(db_session, user)
    assert resp.credit_balance == 0
    assert resp.phone == "13800138000"
```

- [ ] **Step 3: 运行测试**

```bash
cd web
uv run pytest tests/test_auth_service.py -v
```

Expected: 8 个测试全部 PASS

- [ ] **Step 4: 提交**

```bash
git add web/src/aigc_web/services/auth.py web/tests/test_auth_service.py
git commit -m "feat(web): add auth service with login/register and token refresh"
```

---

### Task 10: API 依赖注入 + 测试

**Files:**
- Create: `web/src/aigc_web/dependencies.py`
- Create: `web/tests/test_dependencies.py`

- [ ] **Step 1: 创建 dependencies.py**

```python
# web/src/aigc_web/dependencies.py
"""FastAPI 路由公共依赖。"""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from aigc_web.database import get_db
from aigc_web.models.user import User
from aigc_web.services.auth import get_current_user, get_user_response
from aigc_web.services.sms import VerificationCodeService
from aigc_web.schemas.auth import UserResponse

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login/phone")

_verification_service: VerificationCodeService | None = None


def get_verification_service() -> VerificationCodeService:
    global _verification_service
    if _verification_service is None:
        _verification_service = VerificationCodeService()
    return _verification_service


def set_verification_service(service: VerificationCodeService) -> None:
    """测试用：注入自定义验证码服务。"""
    global _verification_service
    _verification_service = service


async def require_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """从 JWT 解析当前用户。无效/过期返回 401。"""
    try:
        return get_current_user(db, token)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


async def require_current_user_response(
    user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
) -> UserResponse:
    """返回包含积分余额的 UserResponse。"""
    return get_user_response(db, user)
```

- [ ] **Step 2: 创建 test_dependencies.py**

```python
# web/tests/test_dependencies.py
"""依赖注入测试。"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from aigc_web.database import Base, get_db
from aigc_web.dependencies import require_current_user
from aigc_web.models.user import User
from aigc_web.services.token import create_access_token

app = FastAPI()


@app.get("/test-me")
async def test_me(user: User = Depends(require_current_user)):
    return {"phone": user.phone}


def test_require_current_user_valid_token(db_engine):
    Session = __import__("sqlalchemy.orm", fromlist=["sessionmaker"]).sessionmaker(
        bind=db_engine
    )
    session = Session()
    user = User(phone="13800138000", nickname="测试")
    session.add(user)
    session.commit()

    token = create_access_token(user.id)
    app.dependency_overrides[get_db] = lambda: session
    client = TestClient(app)
    resp = client.get("/test-me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["phone"] == "13800138000"
    app.dependency_overrides.clear()
    session.close()


def test_require_current_user_no_token():
    app.dependency_overrides.pop(get_db, None)
    client = TestClient(app)
    resp = client.get("/test-me")
    assert resp.status_code == 401
```

- [ ] **Step 3: 运行测试**

```bash
cd web
uv run pytest tests/test_dependencies.py -v
```

Expected: 2 个测试 PASS

- [ ] **Step 4: 提交**

```bash
git add web/src/aigc_web/dependencies.py web/tests/test_dependencies.py
git commit -m "feat(web): add API dependency injection (auth, SMS service)"
```

---

### Task 11: Auth 路由 + 集成测试

**Files:**
- Create: `web/src/aigc_web/routers/__init__.py`
- Create: `web/src/aigc_web/routers/auth.py`
- Create: `web/tests/test_auth_router.py`

- [ ] **Step 1: 创建 routers/__init__.py**

```python
# web/src/aigc_web/routers/__init__.py
```

- [ ] **Step 2: 创建 routers/auth.py**

```python
# web/src/aigc_web/routers/auth.py
"""认证相关 API 路由。"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from aigc_web.database import get_db
from aigc_web.dependencies import get_verification_service, require_current_user_response
from aigc_web.schemas.auth import (
    LoginResponse,
    MessageResponse,
    PhoneLoginRequest,
    RefreshRequest,
    SendSmsRequest,
    TokenResponse,
    UserResponse,
)
from aigc_web.services import auth as auth_service
from aigc_web.services.sms import VerificationCodeService

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/sms/send", response_model=MessageResponse)
def send_sms(
    req: SendSmsRequest,
    sms: VerificationCodeService = Depends(get_verification_service),
):
    try:
        sms.send(req.phone)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    return MessageResponse(message="验证码已发送")


@router.post("/login/phone", response_model=LoginResponse)
def login_by_phone(req: PhoneLoginRequest, db: Session = Depends(get_db)):
    sms: VerificationCodeService = get_verification_service()
    if not sms.verify(req.phone, req.code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="验证码错误或已过期",
        )
    return auth_service.login_or_register(db, req.phone)


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(req: RefreshRequest, db: Session = Depends(get_db)):
    try:
        new_access = auth_service.refresh_access_token(db, req.refresh_token)
        return TokenResponse(
            access_token=new_access,
            refresh_token=req.refresh_token,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e)
        ) from e


@router.get("/me", response_model=UserResponse)
async def get_me(user: UserResponse = Depends(require_current_user_response)):
    return user
```

- [ ] **Step 3: 创建 test_auth_router.py — API 集成测试**

```python
# web/tests/test_auth_router.py
"""Auth API 集成测试。"""

import pytest
from fastapi.testclient import TestClient

from aigc_web.database import Base, get_db
from aigc_web.dependencies import get_verification_service, set_verification_service
from aigc_web.main import app
from aigc_web.services.sms import VerificationCodeService


@pytest.fixture
def client(db_engine):
    from sqlalchemy.orm import sessionmaker

    Session = sessionmaker(bind=db_engine)
    session = Session()

    sms = VerificationCodeService()
    set_verification_service(sms)

    def override_get_db():
        yield session

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()
    session.close()


def _get_code(sms: VerificationCodeService, phone: str) -> str:
    """从 sms 服务内部取出验证码（测试用）。"""
    sms.send(phone)
    return sms._store[phone].code


def test_send_sms(client):
    resp = client.post("/api/auth/sms/send", json={"phone": "13800138000"})
    assert resp.status_code == 200
    assert resp.json()["message"] == "验证码已发送"


def test_send_sms_invalid_phone(client):
    resp = client.post("/api/auth/sms/send", json={"phone": "123"})
    assert resp.status_code == 422


def test_login_with_valid_code(client):
    sms = get_verification_service()
    code = _get_code(sms, "13800138001")

    resp = client.post(
        "/api/auth/login/phone", json={"phone": "13800138001", "code": code}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["user"]["phone"] == "13800138001"
    assert data["user"]["nickname"] == "用户8001"
    assert data["user"]["credit_balance"] == 0


def test_login_with_wrong_code(client):
    sms = get_verification_service()
    _get_code(sms, "13800138002")

    resp = client.post(
        "/api/auth/login/phone", json={"phone": "13800138002", "code": "000000"}
    )
    assert resp.status_code == 400


def test_get_me_with_valid_token(client):
    sms = get_verification_service()
    code = _get_code(sms, "13800138003")
    login_resp = client.post(
        "/api/auth/login/phone", json={"phone": "13800138003", "code": code}
    )
    token = login_resp.json()["access_token"]

    resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["phone"] == "13800138003"


def test_get_me_without_token(client):
    resp = client.get("/api/auth/me")
    assert resp.status_code == 401


def test_refresh_token(client):
    sms = get_verification_service()
    code = _get_code(sms, "13800138004")
    login_resp = client.post(
        "/api/auth/login/phone", json={"phone": "13800138004", "code": code}
    )
    refresh = login_resp.json()["refresh_token"]

    resp = client.post("/api/auth/refresh", json={"refresh_token": refresh})
    assert resp.status_code == 200
    assert "access_token" in resp.json()
```

- [ ] **Step 4: 运行集成测试**

```bash
cd web
uv run pytest tests/test_auth_router.py -v
```

Expected: 7 个测试全部 PASS

- [ ] **Step 5: 提交**

```bash
git add web/src/aigc_web/routers/ web/tests/test_auth_router.py
git commit -m "feat(web): add auth API routes with integration tests"
```

---

### Task 12: FastAPI 主应用

**Files:**
- Create: `web/src/aigc_web/main.py`

- [ ] **Step 1: 创建 main.py**

```python
# web/src/aigc_web/main.py
"""FastAPI 应用入口。"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from aigc_web.config import settings
from aigc_web.routers import auth as auth_router

app = FastAPI(title="AIGC Reducer", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router)


@app.get("/api/health")
def health_check():
    return {"status": "ok"}
```

- [ ] **Step 2: 启动应用并验证**

```bash
cd web
uv run uvicorn aigc_web.main:app --port 8000
```

在另一个终端访问 `http://localhost:8000/docs`，应看到 Swagger UI，包含：
- `GET /api/health`
- `POST /api/auth/sms/send`
- `POST /api/auth/login/phone`
- `POST /api/auth/refresh`
- `GET /api/auth/me`

- [ ] **Step 3: 运行所有后端测试**

```bash
cd web
uv run pytest tests/ -v --tb=short
```

Expected: 全部 PASS

- [ ] **Step 4: 提交**

```bash
git add web/src/aigc_web/main.py
git commit -m "feat(web): add FastAPI app with CORS and health check"
```

---

### Task 13: 前端脚手架

**Files:**
- Create: `web/frontend/` (由 Vite 生成)
- Modify: `web/frontend/package.json` (添加依赖)

- [ ] **Step 1: 使用 Vite 创建 React + TypeScript 项目**

```bash
cd web
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install
```

- [ ] **Step 2: 安装前端依赖**

```bash
cd web/frontend
npm install antd @ant-design/icons react-router-dom zustand axios
```

- [ ] **Step 3: 清理 Vite 默认文件**

删除 `web/frontend/src/App.css`、`web/frontend/src/index.css`（如有）。

将 `web/frontend/src/App.tsx` 内容替换为：

```tsx
// web/frontend/src/App.tsx
function App() {
  return <div>AIGC Reducer</div>
}

export default App
```

- [ ] **Step 4: 验证前端可启动**

```bash
cd web/frontend
npm run dev
```

访问 `http://localhost:5173`，应看到 "AIGC Reducer" 文字。

- [ ] **Step 5: 提交**

```bash
git add web/frontend/
git commit -m "feat(web): scaffold React frontend with Vite, Ant Design, Zustand"
```

---

### Task 14: API 客户端 + Auth Store

**Files:**
- Create: `web/frontend/src/api/client.ts`
- Create: `web/frontend/src/api/auth.ts`
- Create: `web/frontend/src/stores/auth.ts`

- [ ] **Step 1: 创建 api/client.ts — Axios 实例 + 拦截器**

```typescript
// web/frontend/src/api/client.ts
import axios from "axios";

const client = axios.create({
  baseURL: "/api",
  timeout: 10000,
});

client.interceptors.request.use((config) => {
  const token = localStorage.getItem("access_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

let isRefreshing = false;
let pendingRequests: Array<(token: string) => void> = [];

client.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    if (error.response?.status === 401 && !originalRequest._retry) {
      const refreshToken = localStorage.getItem("refresh_token");
      if (!refreshToken) {
        localStorage.clear();
        window.location.href = "/login";
        return Promise.reject(error);
      }

      if (!isRefreshing) {
        isRefreshing = true;
        originalRequest._retry = true;
        try {
          const resp = await axios.post("/api/auth/refresh", {
            refresh_token: refreshToken,
          });
          const newToken = resp.data.access_token;
          localStorage.setItem("access_token", newToken);
          pendingRequests.forEach((cb) => cb(newToken));
          pendingRequests = [];
          originalRequest.headers.Authorization = `Bearer ${newToken}`;
          return client(originalRequest);
        } catch {
          localStorage.clear();
          window.location.href = "/login";
          return Promise.reject(error);
        } finally {
          isRefreshing = false;
        }
      }

      return new Promise((resolve) => {
        pendingRequests.push((token: string) => {
          originalRequest.headers.Authorization = `Bearer ${token}`;
          resolve(client(originalRequest));
        });
      });
    }
    return Promise.reject(error);
  }
);

export default client;
```

- [ ] **Step 2: 创建 api/auth.ts — 认证 API 函数**

```typescript
// web/frontend/src/api/auth.ts
import client from "./client";

export interface UserResponse {
  id: number;
  phone: string;
  nickname: string;
  avatar_url: string | null;
  is_active: boolean;
  credit_balance: number;
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  user: UserResponse;
}

export async function sendSms(phone: string): Promise<void> {
  await client.post("/auth/sms/send", { phone });
}

export async function loginByPhone(
  phone: string,
  code: string
): Promise<LoginResponse> {
  const resp = await client.post<LoginResponse>("/auth/login/phone", {
    phone,
    code,
  });
  return resp.data;
}

export async function refreshToken(
  refresh_token: string
): Promise<{ access_token: string }> {
  const resp = await client.post("/auth/refresh", { refresh_token });
  return resp.data;
}

export async function getMe(): Promise<UserResponse> {
  const resp = await client.get<UserResponse>("/auth/me");
  return resp.data;
}
```

- [ ] **Step 3: 创建 stores/auth.ts — Zustand 状态管理**

```typescript
// web/frontend/src/stores/auth.ts
import { create } from "zustand";
import {
  getMe,
  loginByPhone,
  sendSms,
  type LoginResponse,
  type UserResponse,
} from "../api/auth";

interface AuthState {
  user: UserResponse | null;
  loading: boolean;
  sendSms: (phone: string) => Promise<void>;
  login: (phone: string, code: string) => Promise<void>;
  fetchUser: () => Promise<void>;
  logout: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  loading: false,

  sendSms: async (phone: string) => {
    await sendSms(phone);
  },

  login: async (phone: string, code: string) => {
    set({ loading: true });
    try {
      const resp: LoginResponse = await loginByPhone(phone, code);
      localStorage.setItem("access_token", resp.access_token);
      localStorage.setItem("refresh_token", resp.refresh_token);
      set({ user: resp.user, loading: false });
    } catch {
      set({ loading: false });
      throw new Error("登录失败");
    }
  },

  fetchUser: async () => {
    try {
      const user = await getMe();
      set({ user });
    } catch {
      set({ user: null });
    }
  },

  logout: () => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    set({ user: null });
  },
}));
```

- [ ] **Step 4: 提交**

```bash
git add web/frontend/src/api/ web/frontend/src/stores/
git commit -m "feat(web): add API client with auth interceptors and Zustand store"
```

---

### Task 15: 登录页面

**Files:**
- Create: `web/frontend/src/pages/Login.tsx`

- [ ] **Step 1: 创建 Login.tsx**

```tsx
// web/frontend/src/pages/Login.tsx
import { useState } from "react";
import { Button, Card, Form, Input, message, Typography } from "antd";
import { MobileOutlined, SafetyOutlined } from "@ant-design/icons";
import { useAuthStore } from "../stores/auth";

const { Title, Text } = Typography;

export default function Login() {
  const [form] = Form.useForm();
  const [sending, setSending] = useState(false);
  const [countdown, setCountdown] = useState(0);
  const { login, sendSms, loading } = useAuthStore();

  const handleSendCode = async () => {
    try {
      const phone = form.getFieldValue("phone");
      if (!phone || !/^1[3-9]\d{9}$/.test(phone)) {
        message.error("请输入正确的手机号");
        return;
      }
      setSending(true);
      await sendSms(phone);
      message.success("验证码已发送（开发模式下查看后端控制台）");
      setCountdown(60);
      const timer = setInterval(() => {
        setCountdown((prev) => {
          if (prev <= 1) {
            clearInterval(timer);
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
    } catch {
      message.error("发送失败，请稍后重试");
    } finally {
      setSending(false);
    }
  };

  const handleLogin = async (values: { phone: string; code: string }) => {
    try {
      await login(values.phone, values.code);
      message.success("登录成功");
    } catch {
      message.error("登录失败，请检查验证码");
    }
  };

  return (
    <div
      style={{
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        minHeight: "100vh",
        background: "#f0f2f5",
      }}
    >
      <Card style={{ width: 400, maxWidth: "90vw" }}>
        <Title level={3} style={{ textAlign: "center", marginBottom: 32 }}>
          AIGC Reducer
        </Title>
        <Form form={form} onFinish={handleLogin} size="large">
          <Form.Item
            name="phone"
            rules={[{ required: true, message: "请输入手机号" }]}
          >
            <Input
              prefix={<MobileOutlined />}
              placeholder="手机号"
              maxLength={11}
            />
          </Form.Item>
          <Form.Item
            name="code"
            rules={[{ required: true, message: "请输入验证码" }]}
          >
            <Input
              prefix={<SafetyOutlined />}
              placeholder="验证码"
              maxLength={6}
              addonAfter={
                <Button
                  type="link"
                  size="small"
                  onClick={handleSendCode}
                  loading={sending}
                  disabled={countdown > 0}
                  style={{ padding: 0 }}
                >
                  {countdown > 0 ? `${countdown}s` : "获取验证码"}
                </Button>
              }
            />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" block loading={loading}>
              登录 / 注册
            </Button>
          </Form.Item>
        </Form>
        <Text
          type="secondary"
          style={{ display: "block", textAlign: "center" }}
        >
          首次登录将自动创建账户
        </Text>
      </Card>
    </div>
  );
}
```

- [ ] **Step 2: 提交**

```bash
git add web/frontend/src/pages/Login.tsx
git commit -m "feat(web): add Login page with phone + SMS code form"
```

---

### Task 16: 全局布局 + 路由守卫 + 全部页面

**Files:**
- Create: `web/frontend/src/components/AppLayout.tsx`
- Create: `web/frontend/src/components/ProtectedRoute.tsx`
- Create: `web/frontend/src/pages/Dashboard.tsx`
- Create: `web/frontend/src/pages/Credits.tsx`
- Create: `web/frontend/src/pages/History.tsx`
- Create: `web/frontend/src/pages/Settings.tsx`
- Modify: `web/frontend/src/App.tsx`
- Modify: `web/frontend/src/main.tsx`

- [ ] **Step 1: 创建 AppLayout.tsx — 全局布局（导航栏 + 内容区）**

```tsx
// web/frontend/src/components/AppLayout.tsx
import { useEffect, useState } from "react";
import { Outlet, useNavigate, useLocation } from "react-router-dom";
import {
  Layout,
  Menu,
  Avatar,
  Dropdown,
  Typography,
  theme,
} from "antd";
import {
  DashboardOutlined,
  CreditCardOutlined,
  HistoryOutlined,
  SettingOutlined,
  LogoutOutlined,
  UserOutlined,
} from "@ant-design/icons";
import { useAuthStore } from "../stores/auth";

const { Header, Content } = Layout;
const { Text } = Typography;

const menuItems = [
  { key: "/dashboard", icon: <DashboardOutlined />, label: "仪表盘" },
  { key: "/credits", icon: <CreditCardOutlined />, label: "积分" },
  { key: "/history", icon: <HistoryOutlined />, label: "历史" },
  { key: "/settings", icon: <SettingOutlined />, label: "设置" },
];

export default function AppLayout() {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, logout, fetchUser } = useAuthStore();
  const { token: themeToken } = theme.useToken();

  useEffect(() => {
    if (!user) {
      fetchUser();
    }
  }, []);

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  const userMenu = {
    items: [
      {
        key: "logout",
        icon: <LogoutOutlined />,
        label: "退出登录",
        onClick: handleLogout,
      },
    ],
  };

  return (
    <Layout style={{ minHeight: "100vh" }}>
      <Header
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "0 24px",
          background: themeToken.colorBgContainer,
          borderBottom: `1px solid ${themeToken.colorBorderSecondary}`,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 24 }}>
          <Text strong style={{ fontSize: 18, whiteSpace: "nowrap" }}>
            AIGC Reducer
          </Text>
          <Menu
            mode="horizontal"
            selectedKeys={[location.pathname]}
            items={menuItems}
            onClick={({ key }) => navigate(key)}
            style={{ border: "none", flex: 1 }}
          />
        </div>
        <Dropdown menu={userMenu} placement="bottomRight">
          <div style={{ cursor: "pointer", display: "flex", alignItems: "center", gap: 8 }}>
            <Avatar icon={<UserOutlined />} />
            <Text style={{ display: "none" }} className="show-on-mobile">
              {user?.nickname}
            </Text>
          </div>
        </Dropdown>
      </Header>
      <Content style={{ padding: "24px", maxWidth: 1200, margin: "0 auto", width: "100%" }}>
        <Outlet />
      </Content>
    </Layout>
  );
}
```

- [ ] **Step 2: 创建 ProtectedRoute.tsx — 路由守卫**

```tsx
// web/frontend/src/components/ProtectedRoute.tsx
import { useEffect, useState } from "react";
import { Navigate } from "react-router-dom";
import { Spin } from "antd";
import { useAuthStore } from "../stores/auth";

export default function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, fetchUser } = useAuthStore();
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (token && !user) {
      fetchUser().finally(() => setChecking(false));
    } else {
      setChecking(false);
    }
  }, []);

  if (checking) {
    return (
      <div style={{ display: "flex", justifyContent: "center", alignItems: "center", minHeight: "100vh" }}>
        <Spin size="large" />
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
}
```

- [ ] **Step 3: 创建 Dashboard.tsx**

```tsx
// web/frontend/src/pages/Dashboard.tsx
import { Card, Col, Row, Statistic, Typography } from "antd";
import { CreditCardOutlined, FileTextOutlined } from "@ant-design/icons";
import { useAuthStore } from "../stores/auth";

const { Title } = Typography;

export default function Dashboard() {
  const { user } = useAuthStore();

  return (
    <div>
      <Title level={4}>欢迎，{user?.nickname}</Title>
      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} sm={12}>
          <Card>
            <Statistic
              title="积分余额"
              value={user?.credit_balance ?? 0}
              prefix={<CreditCardOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12}>
          <Card>
            <Statistic
              title="检测次数"
              value={0}
              prefix={<FileTextOutlined />}
            />
          </Card>
        </Col>
      </Row>
    </div>
  );
}
```

- [ ] **Step 4: 创建 Credits.tsx（占位页面）**

```tsx
// web/frontend/src/pages/Credits.tsx
import { Card, Empty, Typography } from "antd";

const { Title } = Typography;

export default function Credits() {
  return (
    <div>
      <Title level={4}>积分管理</Title>
      <Card>
        <Empty description="充值功能开发中（P2）" />
      </Card>
    </div>
  );
}
```

- [ ] **Step 5: 创建 History.tsx（占位页面）**

```tsx
// web/frontend/src/pages/History.tsx
import { Card, Empty, Typography } from "antd";

const { Title } = Typography;

export default function History() {
  return (
    <div>
      <Title level={4}>检测历史</Title>
      <Card>
        <Empty description="检测功能开发中（P3）" />
      </Card>
    </div>
  );
}
```

- [ ] **Step 6: 创建 Settings.tsx**

```tsx
// web/frontend/src/pages/Settings.tsx
import { Card, Descriptions, Typography } from "antd";
import { useAuthStore } from "../stores/auth";

const { Title } = Typography;

export default function Settings() {
  const { user } = useAuthStore();

  return (
    <div>
      <Title level={4}>个人设置</Title>
      <Card>
        <Descriptions column={1}>
          <Descriptions.Item label="手机号">{user?.phone}</Descriptions.Item>
          <Descriptions.Item label="昵称">{user?.nickname}</Descriptions.Item>
          <Descriptions.Item label="积分余额">{user?.credit_balance}</Descriptions.Item>
        </Descriptions>
      </Card>
    </div>
  );
}
```

- [ ] **Step 7: 更新 App.tsx — 路由定义**

```tsx
// web/frontend/src/App.tsx
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { ConfigProvider } from "antd";
import zhCN from "antd/locale/zh_CN";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import Credits from "./pages/Credits";
import History from "./pages/History";
import Settings from "./pages/Settings";
import AppLayout from "./components/AppLayout";
import ProtectedRoute from "./components/ProtectedRoute";

export default function App() {
  return (
    <ConfigProvider locale={zhCN}>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route
            element={
              <ProtectedRoute>
                <AppLayout />
              </ProtectedRoute>
            }
          >
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/credits" element={<Credits />} />
            <Route path="/history" element={<History />} />
            <Route path="/settings" element={<Settings />} />
          </Route>
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </BrowserRouter>
    </ConfigProvider>
  );
}
```

- [ ] **Step 8: 更新 main.tsx**

```tsx
// web/frontend/src/main.tsx
import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
```

- [ ] **Step 9: 提交**

```bash
git add web/frontend/src/
git commit -m "feat(web): add layout, routing, and all pages"
```

---

### Task 17: Vite 代理配置 + 响应式样式

**Files:**
- Modify: `web/frontend/vite.config.ts`

- [ ] **Step 1: 更新 vite.config.ts — 添加 API 代理**

```typescript
// web/frontend/vite.config.ts
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});
```

- [ ] **Step 2: 添加全局响应式样式**

创建 `web/frontend/src/styles/global.css`：

```css
/* web/frontend/src/styles/global.css */
/* 移动端导航菜单适配 */
@media (max-width: 768px) {
  .ant-menu-horizontal {
    display: none !important;
  }
  .show-on-mobile {
    display: inline !important;
  }
}
```

在 `web/frontend/src/main.tsx` 中添加 import：

```tsx
// 在文件顶部添加
import "./styles/global.css";
```

- [ ] **Step 3: 提交**

```bash
git add web/frontend/vite.config.ts web/frontend/src/styles/ web/frontend/src/main.tsx
git commit -m "feat(web): add Vite proxy config and responsive styles"
```

---

### Task 18: 端到端验证

此任务为手动验证，不提交代码。

- [ ] **Step 1: 启动后端**

```bash
cd web
uv run uvicorn aigc_web.main:app --reload --port 8000
```

- [ ] **Step 2: 启动前端**

```bash
cd web/frontend
npm run dev
```

- [ ] **Step 3: 验证 Swagger UI**

浏览器打开 `http://localhost:8000/docs`，确认 4 个 auth 接口 + health check 都显示。

- [ ] **Step 4: 验证完整登录流程**

1. 打开 `http://localhost:5173`，自动跳转到 `/login`
2. 输入手机号，点击"获取验证码"
3. 在后端控制台查看验证码（`[DEV SMS] 验证码 xxxxxx -> 138xxxxxxxx`）
4. 输入验证码，点击"登录/注册"
5. 登录成功后跳转到 `/dashboard`，显示积分余额 0
6. 点击"积分"、"历史"、"设置"页面可正常切换
7. 刷新页面不会丢失登录状态（Token 自动恢复）

- [ ] **Step 5: 验证响应式**

在浏览器中切换到手机尺寸，确认：
- 导航菜单隐藏
- 登录卡片不超出屏幕
- Dashboard 统计卡片单列显示

- [ ] **Step 6: 运行全部后端测试**

```bash
cd web
uv run pytest tests/ -v --cov=aigc_web
```

Expected: 全部 PASS，覆盖率报告正常

---

## Self-Review Checklist

- [x] **Spec coverage:** 设计文档中所有要求（项目结构、数据库模型、认证系统、前端框架、配置管理）都有对应的 Task 实现
- [x] **Placeholder scan:** 无 TBD/TODO/待实现内容，每个步骤都有完整代码
- [x] **Type consistency:** 函数名、参数名、类型在各 Task 中保持一致（如 `login_or_register`、`VerificationCodeService`、`UserResponse`）
- [x] **Spec 的 4 个验证方式**：Swagger UI (Task 12/18)、注册登录 (Task 11/18)、Token 认证 (Task 11/18)、前端页面 (Task 18)

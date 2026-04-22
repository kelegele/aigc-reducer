# P2.5: 账号角色体系与超管后台 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建立账号角色体系，超管可管理套餐、积分配置、用户和数据看板；开发环境支持测试账号跳过验证码。

**Architecture:** 后端新增 `require_admin` 依赖 + `services/admin.py` + `routers/admin.py`（10 个端点）。复用现有 `is_admin` 字段和积分服务。前端在现有应用中增加 4 个管理页面，超管导航栏自动显示"管理"菜单。

**Tech Stack:** FastAPI + SQLAlchemy 2.0（后端）；React 19 + TypeScript + Ant Design（前端）

---

## File Structure

### 后端新增/修改文件

| 操作 | 路径 | 职责 |
|------|------|------|
| Modify | `web/src/aigc_web/config.py` | 新增 DEV_TEST_PHONES、DEV_BYPASS_PHONE |
| Modify | `web/src/aigc_web/dependencies.py` | 新增 require_admin 依赖 |
| Modify | `web/src/aigc_web/services/sms.py` | 开发环境跳过验证码 |
| Create | `web/src/aigc_web/schemas/admin.py` | 管理 API 请求/响应模型 |
| Create | `web/src/aigc_web/services/admin.py` | 管理服务（套餐CRUD、用户管理、看板、配置） |
| Create | `web/src/aigc_web/routers/admin.py` | 管理 API 路由（10 端点） |
| Modify | `web/src/aigc_web/main.py` | 注册 admin 路由 |
| Create | `web/tests/test_admin_service.py` | 管理服务单元测试 |
| Create | `web/tests/test_admin_router.py` | 管理 API 集成测试 |

### 前端新增/修改文件

| 操作 | 路径 | 职责 |
|------|------|------|
| Create | `web/frontend/src/api/admin.ts` | 管理 API 调用函数 |
| Modify | `web/frontend/src/components/AppLayout.tsx` | 超管菜单 |
| Modify | `web/frontend/src/App.tsx` | 注册 admin 路由 |
| Modify | `web/frontend/src/api/auth.ts` | UserResponse 增加 is_admin |
| Create | `web/frontend/src/pages/admin/AdminDashboard.tsx` | 数据看板 |
| Create | `web/frontend/src/pages/admin/AdminPackages.tsx` | 套餐管理 |
| Create | `web/frontend/src/pages/admin/AdminUsers.tsx` | 用户管理 |
| Create | `web/frontend/src/pages/admin/AdminConfig.tsx` | 积分配置 |

---

## Task 1: 新增配置项

**Files:**
- Modify: `web/src/aigc_web/config.py`

- [ ] **Step 1: 在 config.py 的 Settings 类中，`ALIPAY_DEBUG` 之后、`model_config` 之前，添加：**

```python
    # 开发环境测试账号
    DEV_TEST_PHONES: str = ""
    DEV_BYPASS_PHONE: bool = False
```

- [ ] **Step 2: 验证配置加载**

Run: `cd F:/dev/aigc-reducer/web && uv run python -c "from aigc_web.config import settings; print(settings.DEV_TEST_PHONES, settings.DEV_BYPASS_PHONE)"`

Expected: ` False`

- [ ] **Step 3: Commit**

```bash
git add web/src/aigc_web/config.py
git commit -m "feat(web): add DEV_TEST_PHONES and DEV_BYPASS_PHONE config"
```

---

## Task 2: 开发环境跳过验证码 + require_admin 依赖

**Files:**
- Modify: `web/src/aigc_web/services/sms.py`
- Modify: `web/src/aigc_web/dependencies.py`
- Create: `web/tests/test_admin_auth.py`

- [ ] **Step 1: 编写测试**

Create `web/tests/test_admin_auth.py`:

```python
# web/tests/test_admin_auth.py
"""管理员权限和开发环境验证码跳过测试。"""

import pytest
from fastapi import HTTPException
from fastapi.security import OAuth2PasswordBearer

from aigc_web.models.credit_account import CreditAccount
from aigc_web.models.user import User
from aigc_web.services import sms as sms_service
from aigc_web.services.token import create_access_token


def test_require_admin_non_admin(db_session):
    """非管理员调用 require_admin 应抛 403。"""
    from aigc_web.dependencies import require_admin

    user = User(phone="13800138000", nickname="普通用户", is_admin=False)
    db_session.add(user)
    db_session.commit()
    token = create_access_token(user.id)

    import asyncio
    with pytest.raises(HTTPException) as exc_info:
        asyncio.get_event_loop().run_until_complete(require_admin(token=token, db=db_session))
    assert exc_info.value.status_code == 403


def test_require_admin_is_admin(db_session):
    """管理员调用 require_admin 应返回 User。"""
    from aigc_web.dependencies import require_admin

    user = User(phone="13800138001", nickname="管理员", is_admin=True)
    db_session.add(user)
    db_session.commit()
    token = create_access_token(user.id)

    import asyncio
    result = asyncio.get_event_loop().run_until_complete(require_admin(token=token, db=db_session))
    assert result.id == user.id
    assert result.is_admin is True


def test_dev_bypass_all_phones(db_session, monkeypatch):
    """DEV_BYPASS_PHONE=True 时所有手机号跳过验证码。"""
    from aigc_web import config
    monkeypatch.setattr(config.settings, "DEV_BYPASS_PHONE", True)
    monkeypatch.setattr(config.settings, "SMS_PROVIDER", "dev")

    svc = sms_service.VerificationCodeService()
    assert svc.verify("13800138000", "000000") is True
    assert svc.verify("13999999999", "123456") is True


def test_dev_bypass_test_phones_only(db_session, monkeypatch):
    """DEV_TEST_PHONES 配置时仅指定手机号跳过。"""
    from aigc_web import config
    monkeypatch.setattr(config.settings, "DEV_TEST_PHONES", "13800138000,13800138001")
    monkeypatch.setattr(config.settings, "DEV_BYPASS_PHONE", False)
    monkeypatch.setattr(config.settings, "SMS_PROVIDER", "dev")

    svc = sms_service.VerificationCodeService()
    assert svc.verify("13800138000", "000000") is True
    assert svc.verify("13800138001", "123456") is True
    assert svc.verify("13999999999", "000000") is False


def test_dev_bypass_not_dev_provider(db_session, monkeypatch):
    """非 dev 模式下不跳过验证码。"""
    from aigc_web import config
    monkeypatch.setattr(config.settings, "DEV_BYPASS_PHONE", True)
    monkeypatch.setattr(config.settings, "SMS_PROVIDER", "aliyun")

    svc = sms_service.VerificationCodeService()
    assert svc.verify("13800138000", "000000") is False
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd F:/dev/aigc-reducer/web && uv run pytest tests/test_admin_auth.py -v`

Expected: FAIL

- [ ] **Step 3: 修改 SMS 服务**

在 `web/src/aigc_web/services/sms.py` 的 `verify` 方法中，在 `entry = self._store.get(phone)` **之前**，添加开发环境跳过逻辑：

```python
    def verify(self, phone: str, code: str) -> bool:
        """校验验证码。成功后清除，防止重复使用。"""
        # 开发环境跳过验证码
        if settings.SMS_PROVIDER == "dev":
            bypass_phones = [p.strip() for p in settings.DEV_TEST_PHONES.split(",") if p.strip()]
            if settings.DEV_BYPASS_PHONE or phone in bypass_phones:
                return True

        entry = self._store.get(phone)
        # ... 后续代码不变
```

- [ ] **Step 4: 在 dependencies.py 新增 require_admin**

在 `web/src/aigc_web/dependencies.py` 末尾追加：

```python
async def require_admin(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """验证当前用户是管理员。非管理员返回 403。"""
    user = await require_current_user(token=token, db=db)
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限",
        )
    return user
```

- [ ] **Step 5: 运行测试确认通过**

Run: `cd F:/dev/aigc-reducer/web && uv run pytest tests/test_admin_auth.py -v`

Expected: 全部 PASS

- [ ] **Step 6: Commit**

```bash
git add web/src/aigc_web/services/sms.py web/src/aigc_web/dependencies.py web/tests/test_admin_auth.py
git commit -m "feat(web): add require_admin dependency and dev SMS bypass"
```

---

## Task 3: Admin Schema

**Files:**
- Create: `web/src/aigc_web/schemas/admin.py`

- [ ] **Step 1: 创建管理 Schema**

```python
# web/src/aigc_web/schemas/admin.py
"""管理后台请求/响应模型。"""

from datetime import datetime

from pydantic import BaseModel


# --- 套餐管理 ---

class PackageCreateRequest(BaseModel):
    name: str
    price_cents: int
    credits: int
    bonus_credits: int = 0
    sort_order: int = 0
    is_active: bool = True


class PackageUpdateRequest(BaseModel):
    name: str | None = None
    price_cents: int | None = None
    credits: int | None = None
    bonus_credits: int | None = None
    sort_order: int | None = None
    is_active: bool | None = None


class AdminPackageResponse(BaseModel):
    id: int
    name: str
    price_cents: int
    credits: int
    bonus_credits: int
    sort_order: int
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# --- 用户管理 ---

class AdminUserResponse(BaseModel):
    id: int
    phone: str
    nickname: str
    is_active: bool
    is_admin: bool
    created_at: datetime
    credit_balance: int
    total_recharged: int
    total_consumed: int


class UserListResponse(BaseModel):
    items: list[AdminUserResponse]
    total: int
    page: int
    size: int


class AdjustCreditsRequest(BaseModel):
    amount: int
    remark: str = "管理员调整"


class SetUserStatusRequest(BaseModel):
    is_active: bool


# --- 看板 ---

class TopUserEntry(BaseModel):
    user_id: int
    nickname: str
    phone: str
    amount: int


class DashboardResponse(BaseModel):
    total_users: int
    total_revenue_cents: int
    total_credits_granted: int
    total_credits_consumed: int
    today_new_users: int
    top_recharge_users: list[TopUserEntry]
    top_consume_users: list[TopUserEntry]


# --- 配置 ---

class ConfigResponse(BaseModel):
    credits_per_token: float
    new_user_bonus_credits: int


class ConfigUpdateRequest(BaseModel):
    credits_per_token: float | None = None
    new_user_bonus_credits: int | None = None
```

- [ ] **Step 2: 验证导入**

Run: `cd F:/dev/aigc-reducer/web && uv run python -c "from aigc_web.schemas.admin import DashboardResponse, PackageCreateRequest; print('OK')"`

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add web/src/aigc_web/schemas/admin.py
git commit -m "feat(web): add admin request/response schemas"
```

---

## Task 4: Admin 服务

**Files:**
- Create: `web/src/aigc_web/services/admin.py`
- Create: `web/tests/test_admin_service.py`

- [ ] **Step 1: 编写测试**

Create `web/tests/test_admin_service.py`:

```python
# web/tests/test_admin_service.py
"""管理服务单元测试。"""

from datetime import datetime, timezone

import pytest

from aigc_web.models.credit_account import CreditAccount
from aigc_web.models.credit_transaction import CreditTransaction
from aigc_web.models.payment_order import PaymentOrder
from aigc_web.models.recharge_package import RechargePackage
from aigc_web.models.user import User
from aigc_web.services import admin as admin_service
from aigc_web.services import credit as credit_service


def _create_admin(db_session):
    user = User(phone="13900000000", nickname="超管", is_admin=True)
    db_session.add(user)
    db_session.commit()
    account = CreditAccount(user_id=user.id)
    db_session.add(account)
    db_session.commit()
    return user


def _create_user(db_session, phone="13800138000"):
    user = User(phone=phone, nickname=f"用户{phone[-4:]}")
    db_session.add(user)
    db_session.commit()
    account = CreditAccount(user_id=user.id)
    db_session.add(account)
    db_session.commit()
    return user


# --- 套餐管理 ---

def test_list_packages(db_session):
    for i, name in enumerate(["基础包", "专业包"]):
        pkg = RechargePackage(
            name=name, price_cents=(i + 1) * 1000,
            credits=(i + 1) * 100, sort_order=i, is_active=(i == 0),
        )
        db_session.add(pkg)
    db_session.commit()

    pkgs = admin_service.list_packages(db_session)
    assert len(pkgs) == 2
    assert pkgs[0].name == "基础包"  # sort_order=0


def test_create_package(db_session):
    data = admin_service.PackageCreateRequest(
        name="测试包", price_cents=500, credits=50, bonus_credits=5,
    )
    pkg = admin_service.create_package(db_session, data)
    assert pkg.id > 0
    assert pkg.name == "测试包"
    assert pkg.price_cents == 500
    assert pkg.is_active is True


def test_update_package(db_session):
    pkg = RechargePackage(name="旧名", price_cents=1000, credits=100)
    db_session.add(pkg)
    db_session.commit()

    data = admin_service.PackageUpdateRequest(name="新名", is_active=False)
    updated = admin_service.update_package(db_session, pkg.id, data)
    assert updated.name == "新名"
    assert updated.is_active is False


def test_update_package_partial(db_session):
    pkg = RechargePackage(name="套餐", price_cents=1000, credits=100, bonus_credits=0)
    db_session.add(pkg)
    db_session.commit()

    data = admin_service.PackageUpdateRequest(bonus_credits=10)
    updated = admin_service.update_package(db_session, pkg.id, data)
    assert updated.bonus_credits == 10
    assert updated.name == "套餐"  # 未修改


def test_delete_package(db_session):
    pkg = RechargePackage(name="删除测试", price_cents=100, credits=10)
    db_session.add(pkg)
    db_session.commit()

    admin_service.delete_package(db_session, pkg.id)
    assert db_session.query(RechargePackage).count() == 0


def test_delete_package_with_orders(db_session):
    user = _create_user(db_session)
    pkg = RechargePackage(name="有订单", price_cents=100, credits=10)
    db_session.add(pkg)
    db_session.commit()

    order = PaymentOrder(
        user_id=user.id, package_id=pkg.id, out_trade_no="PAY_DEL_TEST",
        amount_cents=100, credits_granted=10, status="pending", pay_method="pc_web",
    )
    db_session.add(order)
    db_session.commit()

    with pytest.raises(ValueError, match="存在关联订单"):
        admin_service.delete_package(db_session, pkg.id)


# --- 用户管理 ---

def test_list_users(db_session):
    _create_user(db_session, "13800138001")
    _create_user(db_session, "13800138002")

    result = admin_service.list_users(db_session, page=1, size=10)
    assert result["total"] == 2
    assert len(result["items"]) == 2


def test_list_users_search(db_session):
    _create_user(db_session, "13800138001")
    _create_user(db_session, "13800138002")

    result = admin_service.list_users(db_session, search="13800138001")
    assert result["total"] == 1


def test_adjust_credits_positive(db_session):
    user = _create_user(db_session)

    admin_service.adjust_credits(db_session, user.id, 100, "测试加积分")

    account = db_session.query(CreditAccount).filter_by(user_id=user.id).one()
    assert account.balance == 100

    tx = db_session.query(CreditTransaction).one()
    assert tx.amount == 100
    assert tx.remark == "测试加积分"


def test_adjust_credits_negative(db_session):
    user = _create_user(db_session)
    credit_service.recharge(db_session, user.id, 200, remark="初始")

    admin_service.adjust_credits(db_session, user.id, -50, "测试扣积分")

    account = db_session.query(CreditAccount).filter_by(user_id=user.id).one()
    assert account.balance == 150


def test_adjust_credits_insufficient(db_session):
    user = _create_user(db_session)

    with pytest.raises(ValueError, match="积分余额不足"):
        admin_service.adjust_credits(db_session, user.id, -100, "超额扣")


def test_set_user_status(db_session):
    user = _create_user(db_session)
    assert user.is_active is True

    admin_service.set_user_status(db_session, user.id, False)
    db_session.refresh(user)
    assert user.is_active is False

    admin_service.set_user_status(db_session, user.id, True)
    db_session.refresh(user)
    assert user.is_active is True


# --- 看板 ---

def test_get_dashboard(db_session):
    user = _create_user(db_session)
    credit_service.recharge(db_session, user.id, 100, remark="充值")

    pkg = RechargePackage(name="包", price_cents=1000, credits=100)
    db_session.add(pkg)
    db_session.commit()

    order = PaymentOrder(
        user_id=user.id, package_id=pkg.id, out_trade_no="PAY_DASH_TEST",
        amount_cents=1000, credits_granted=100, status="paid", pay_method="pc_web",
        paid_at=datetime.now(timezone.utc),
    )
    db_session.add(order)
    db_session.commit()

    result = admin_service.get_dashboard(db_session)
    assert result["total_users"] == 1
    assert result["total_revenue_cents"] == 1000
    assert result["today_new_users"] == 1
    assert len(result["top_recharge_users"]) <= 10


# --- 配置 ---

def test_get_config():
    result = admin_service.get_config()
    assert "credits_per_token" in result
    assert "new_user_bonus_credits" in result


def test_update_config(monkeypatch):
    from aigc_web import config
    admin_service.update_config(
        config.settings, credits_per_token=2.0, new_user_bonus_credits=100,
    )
    assert config.settings.CREDITS_PER_TOKEN == 2.0
    assert config.settings.NEW_USER_BONUS_CREDITS == 100
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd F:/dev/aigc-reducer/web && uv run pytest tests/test_admin_service.py -v`

Expected: FAIL

- [ ] **Step 3: 实现管理服务**

```python
# web/src/aigc_web/services/admin.py
"""管理服务 — 套餐CRUD、用户管理、数据看板、配置管理。"""

from datetime import datetime, timezone

from sqlalchemy import func as sa_func
from sqlalchemy.orm import Session

from aigc_web.models.credit_account import CreditAccount
from aigc_web.models.credit_transaction import CreditTransaction
from aigc_web.models.payment_order import PaymentOrder
from aigc_web.models.recharge_package import RechargePackage
from aigc_web.models.user import User
from aigc_web.schemas.admin import PackageCreateRequest, PackageUpdateRequest
from aigc_web.services import credit as credit_service


# --- 套餐管理 ---

def list_packages(db: Session) -> list[RechargePackage]:
    return db.query(RechargePackage).order_by(RechargePackage.sort_order).all()


def create_package(db: Session, data: PackageCreateRequest) -> RechargePackage:
    pkg = RechargePackage(
        name=data.name,
        price_cents=data.price_cents,
        credits=data.credits,
        bonus_credits=data.bonus_credits,
        sort_order=data.sort_order,
        is_active=data.is_active,
    )
    db.add(pkg)
    db.commit()
    db.refresh(pkg)
    return pkg


def update_package(db: Session, package_id: int, data: PackageUpdateRequest) -> RechargePackage:
    pkg = db.query(RechargePackage).filter_by(id=package_id).one()
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(pkg, field, value)
    db.commit()
    db.refresh(pkg)
    return pkg


def delete_package(db: Session, package_id: int) -> None:
    order_count = db.query(PaymentOrder).filter_by(package_id=package_id).count()
    if order_count > 0:
        raise ValueError("存在关联订单，无法删除")
    pkg = db.query(RechargePackage).filter_by(id=package_id).one()
    db.delete(pkg)
    db.commit()


# --- 用户管理 ---

def list_users(
    db: Session,
    search: str | None = None,
    page: int = 1,
    size: int = 20,
) -> dict:
    query = db.query(User)
    if search:
        query = query.filter(
            (User.phone.contains(search)) | (User.nickname.contains(search))
        )

    total = query.count()
    users = query.order_by(User.id.desc()).offset((page - 1) * size).limit(size).all()

    items = []
    for user in users:
        account = db.query(CreditAccount).filter_by(user_id=user.id).first()
        items.append({
            "id": user.id,
            "phone": user.phone,
            "nickname": user.nickname,
            "is_active": user.is_active,
            "is_admin": user.is_admin,
            "created_at": user.created_at,
            "credit_balance": account.balance if account else 0,
            "total_recharged": account.total_recharged if account else 0,
            "total_consumed": account.total_consumed if account else 0,
        })
    return {"items": items, "total": total, "page": page, "size": size}


def adjust_credits(db: Session, user_id: int, amount: int, remark: str) -> None:
    """手动调整积分。正数加，负数减。"""
    if amount == 0:
        return

    if amount > 0:
        credit_service.recharge(db, user_id, amount, ref_type="admin_adjust", remark=remark)
    else:
        account = db.query(CreditAccount).filter_by(user_id=user_id).with_for_update().one()
        if account.balance < abs(amount):
            raise ValueError(f"积分余额不足，当前 {account.balance}，需扣除 {abs(amount)}")

        account.balance -= abs(amount)
        account.total_consumed += abs(amount)

        tx = CreditTransaction(
            user_id=user_id,
            type="consume",
            amount=amount,
            balance_after=account.balance,
            ref_type="admin_adjust",
            remark=remark,
        )
        db.add(tx)
        db.commit()


def set_user_status(db: Session, user_id: int, is_active: bool) -> None:
    user = db.query(User).filter_by(id=user_id).one()
    user.is_active = is_active
    db.commit()


# --- 看板 ---

def get_dashboard(db: Session) -> dict:
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    total_users = db.query(sa_func.count(User.id)).scalar()
    total_revenue = db.query(sa_func.coalesce(sa_func.sum(PaymentOrder.amount_cents), 0)).filter(
        PaymentOrder.status == "paid"
    ).scalar()
    total_granted = db.query(sa_func.coalesce(sa_func.sum(CreditAccount.total_recharged), 0)).scalar()
    total_consumed = db.query(sa_func.coalesce(sa_func.sum(CreditAccount.total_consumed), 0)).scalar()
    today_new = db.query(sa_func.count(User.id)).filter(User.created_at >= today_start).scalar()

    # Top 10 充值用户
    top_recharge = (
        db.query(
            CreditAccount.user_id,
            User.nickname,
            User.phone,
            CreditAccount.total_recharged.label("amount"),
        )
        .join(User, User.id == CreditAccount.user_id)
        .order_by(CreditAccount.total_recharged.desc())
        .limit(10)
        .all()
    )

    # Top 10 消费用户
    top_consume = (
        db.query(
            CreditAccount.user_id,
            User.nickname,
            User.phone,
            CreditAccount.total_consumed.label("amount"),
        )
        .join(User, User.id == CreditAccount.user_id)
        .order_by(CreditAccount.total_consumed.desc())
        .limit(10)
        .all()
    )

    return {
        "total_users": total_users,
        "total_revenue_cents": total_revenue,
        "total_credits_granted": total_granted,
        "total_credits_consumed": total_consumed,
        "today_new_users": today_new,
        "top_recharge_users": [
            {"user_id": r.user_id, "nickname": r.nickname, "phone": r.phone, "amount": r.amount}
            for r in top_recharge
        ],
        "top_consume_users": [
            {"user_id": r.user_id, "nickname": r.nickname, "phone": r.phone, "amount": r.amount}
            for r in top_consume
        ],
    }


# --- 配置 ---

def get_config() -> dict:
    from aigc_web.config import settings
    return {
        "credits_per_token": settings.CREDITS_PER_TOKEN,
        "new_user_bonus_credits": settings.NEW_USER_BONUS_CREDITS,
    }


def update_config(settings_obj, credits_per_token: float | None = None, new_user_bonus_credits: int | None = None) -> None:
    """更新运行时配置。注意：仅运行时生效，不持久化到 .env。"""
    if credits_per_token is not None:
        settings_obj.CREDITS_PER_TOKEN = credits_per_token
    if new_user_bonus_credits is not None:
        settings_obj.NEW_USER_BONUS_CREDITS = new_user_bonus_credits
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd F:/dev/aigc-reducer/web && uv run pytest tests/test_admin_service.py -v`

Expected: 全部 PASS

- [ ] **Step 5: 运行全量测试确认无回归**

Run: `cd F:/dev/aigc-reducer/web && uv run pytest tests/ -v`

Expected: 全部 PASS

- [ ] **Step 6: Commit**

```bash
git add web/src/aigc_web/services/admin.py web/tests/test_admin_service.py
git commit -m "feat(web): add admin service with package CRUD, user management, dashboard"
```

---

## Task 5: Admin 路由 + 集成测试

**Files:**
- Create: `web/src/aigc_web/routers/admin.py`
- Modify: `web/src/aigc_web/main.py`
- Create: `web/tests/test_admin_router.py`

- [ ] **Step 1: 创建管理路由**

```python
# web/src/aigc_web/routers/admin.py
"""管理后台 API 路由。"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from aigc_web.config import settings
from aigc_web.database import get_db
from aigc_web.dependencies import require_admin
from aigc_web.models.user import User
from aigc_web.schemas.admin import (
    AdjustCreditsRequest,
    AdminPackageResponse,
    ConfigResponse,
    ConfigUpdateRequest,
    DashboardResponse,
    PackageCreateRequest,
    PackageUpdateRequest,
    SetUserStatusRequest,
    UserListResponse,
)
from aigc_web.schemas.auth import MessageResponse
from aigc_web.services import admin as admin_service

router = APIRouter(prefix="/api/admin", tags=["admin"])


# --- 看板 ---

@router.get("/dashboard", response_model=DashboardResponse)
def get_dashboard(
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return admin_service.get_dashboard(db)


# --- 套餐管理 ---

@router.get("/packages", response_model=list[AdminPackageResponse])
def list_packages(
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return admin_service.list_packages(db)


@router.post("/packages", response_model=AdminPackageResponse)
def create_package(
    req: PackageCreateRequest,
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return admin_service.create_package(db, req)


@router.put("/packages/{package_id}", response_model=AdminPackageResponse)
def update_package(
    package_id: int,
    req: PackageUpdateRequest,
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    try:
        return admin_service.update_package(db, package_id, req)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.delete("/packages/{package_id}", response_model=MessageResponse)
def delete_package(
    package_id: int,
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    try:
        admin_service.delete_package(db, package_id)
        return MessageResponse(message="删除成功")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


# --- 用户管理 ---

@router.get("/users", response_model=UserListResponse)
def list_users(
    search: str | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    result = admin_service.list_users(db, search=search, page=page, size=size)
    return UserListResponse(**result)


@router.put("/users/{user_id}/credits", response_model=MessageResponse)
def adjust_credits(
    user_id: int,
    req: AdjustCreditsRequest,
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    try:
        admin_service.adjust_credits(db, user_id, req.amount, req.remark)
        return MessageResponse(message="积分调整成功")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.put("/users/{user_id}/status", response_model=MessageResponse)
def set_user_status(
    user_id: int,
    req: SetUserStatusRequest,
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    try:
        admin_service.set_user_status(db, user_id, req.is_active)
        return MessageResponse(message="状态更新成功")
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


# --- 配置 ---

@router.get("/config", response_model=ConfigResponse)
def get_config(
    _admin: User = Depends(require_admin),
):
    return admin_service.get_config()


@router.put("/config", response_model=ConfigResponse)
def update_config(
    req: ConfigUpdateRequest,
    _admin: User = Depends(require_admin),
):
    admin_service.update_config(
        settings,
        credits_per_token=req.credits_per_token,
        new_user_bonus_credits=req.new_user_bonus_credits,
    )
    return admin_service.get_config()
```

- [ ] **Step 2: 在 main.py 注册路由**

在 `web/src/aigc_web/main.py` 中添加导入和注册：

在 import 区域添加：
```python
from aigc_web.routers import admin as admin_router
```

在 `app.include_router(credits_router.router)` 之后添加：
```python
app.include_router(admin_router.router)
```

- [ ] **Step 3: 编写集成测试**

Create `web/tests/test_admin_router.py`:

```python
# web/tests/test_admin_router.py
"""管理后台 API 集成测试。"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from aigc_web.database import Base, get_db
from aigc_web.dependencies import set_verification_service
from aigc_web.main import app
from aigc_web.models.credit_account import CreditAccount
from aigc_web.models.recharge_package import RechargePackage
from aigc_web.models.user import User
from aigc_web.services.payment import MockPaymentProvider, set_payment_provider
from aigc_web.services.sms import VerificationCodeService
from aigc_web.services.token import create_access_token

_db_session = None


@pytest.fixture
def client():
    global _db_session
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    _db_session = Session()

    sms = VerificationCodeService()
    set_verification_service(sms)
    set_payment_provider(MockPaymentProvider())

    def override_get_db():
        yield _db_session

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()
    _db_session.close()
    engine.dispose()


def _db():
    return _db_session


def _create_admin():
    db = _db()
    user = User(phone="13900000000", nickname="超管", is_admin=True)
    db.add(user)
    db.commit()
    account = CreditAccount(user_id=user.id)
    db.add(account)
    db.commit()
    return create_access_token(user.id), user.id


def _create_normal_user():
    db = _db()
    user = User(phone="13800138000", nickname="普通用户", is_admin=False)
    db.add(user)
    db.commit()
    account = CreditAccount(user_id=user.id)
    db.add(account)
    db.commit()
    return create_access_token(user.id)


def test_admin_access_allowed(client):
    token, _ = _create_admin()
    resp = client.get("/api/admin/dashboard", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200


def test_admin_access_forbidden(client):
    token = _create_normal_user()
    resp = client.get("/api/admin/dashboard", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403


def test_admin_access_no_token(client):
    resp = client.get("/api/admin/dashboard")
    assert resp.status_code == 401


def test_dashboard(client):
    token, _ = _create_admin()
    resp = client.get("/api/admin/dashboard", headers={"Authorization": f"Bearer {token}"})
    data = resp.json()
    assert data["total_users"] >= 0
    assert "top_recharge_users" in data


def test_crud_packages(client):
    token, _ = _create_admin()
    headers = {"Authorization": f"Bearer {token}"}

    # 创建
    resp = client.post("/api/admin/packages", json={
        "name": "测试包", "price_cents": 500, "credits": 50,
    }, headers=headers)
    assert resp.status_code == 200
    pkg_id = resp.json()["id"]

    # 列表
    resp = client.get("/api/admin/packages", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) >= 1

    # 修改
    resp = client.put(f"/api/admin/packages/{pkg_id}", json={"name": "改名"}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["name"] == "改名"

    # 删除
    resp = client.delete(f"/api/admin/packages/{pkg_id}", headers=headers)
    assert resp.status_code == 200


def test_list_users(client):
    token, _ = _create_admin()
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.get("/api/admin/users", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["total"] >= 1


def test_list_users_search(client):
    token, _ = _create_admin()
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.get("/api/admin/users", params={"search": "13900000000"}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["total"] == 1


def test_adjust_credits(client):
    token, admin_id = _create_admin()
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.put(f"/api/admin/users/{admin_id}/credits", json={
        "amount": 100, "remark": "测试加积分",
    }, headers=headers)
    assert resp.status_code == 200


def test_set_user_status(client):
    token, _ = _create_admin()
    headers = {"Authorization": f"Bearer {token}"}
    user_token = _create_normal_user()
    db = _db()
    user = db.query(User).filter(User.phone == "13800138000").first()

    resp = client.put(f"/api/admin/users/{user.id}/status", json={"is_active": False}, headers=headers)
    assert resp.status_code == 200


def test_get_config(client):
    token, _ = _create_admin()
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.get("/api/admin/config", headers=headers)
    assert resp.status_code == 200
    assert "credits_per_token" in resp.json()


def test_update_config(client):
    token, _ = _create_admin()
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.put("/api/admin/config", json={"credits_per_token": 2.0}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["credits_per_token"] == 2.0
```

- [ ] **Step 4: 运行全量测试**

Run: `cd F:/dev/aigc-reducer/web && uv run pytest tests/ -v`

Expected: 全部 PASS

- [ ] **Step 5: Commit**

```bash
git add web/src/aigc_web/routers/admin.py web/src/aigc_web/main.py web/tests/test_admin_router.py
git commit -m "feat(web): add admin API routes with integration tests"
```

---

## Task 6: 前端 — Admin API + 路由 + AppLayout

**Files:**
- Create: `web/frontend/src/api/admin.ts`
- Modify: `web/frontend/src/api/auth.ts` — UserResponse 增加 is_admin
- Modify: `web/frontend/src/components/AppLayout.tsx` — 超管菜单
- Modify: `web/frontend/src/App.tsx` — 注册 admin 路由

- [ ] **Step 1: 创建 admin API 客户端**

```typescript
// web/frontend/src/api/admin.ts
import client from "./client";

// --- Types ---

export interface AdminPackageResponse {
  id: number;
  name: string;
  price_cents: number;
  credits: number;
  bonus_credits: number;
  sort_order: number;
  is_active: boolean;
  created_at: string;
}

export interface PackageCreateRequest {
  name: string;
  price_cents: number;
  credits: number;
  bonus_credits?: number;
  sort_order?: number;
  is_active?: boolean;
}

export interface PackageUpdateRequest {
  name?: string;
  price_cents?: number;
  credits?: number;
  bonus_credits?: number;
  sort_order?: number;
  is_active?: boolean;
}

export interface AdminUserResponse {
  id: number;
  phone: string;
  nickname: string;
  is_active: boolean;
  is_admin: boolean;
  created_at: string;
  credit_balance: number;
  total_recharged: number;
  total_consumed: number;
}

export interface UserListResponse {
  items: AdminUserResponse[];
  total: number;
  page: number;
  size: number;
}

export interface TopUserEntry {
  user_id: number;
  nickname: string;
  phone: string;
  amount: number;
}

export interface DashboardResponse {
  total_users: number;
  total_revenue_cents: number;
  total_credits_granted: number;
  total_credits_consumed: number;
  today_new_users: number;
  top_recharge_users: TopUserEntry[];
  top_consume_users: TopUserEntry[];
}

export interface ConfigResponse {
  credits_per_token: number;
  new_user_bonus_credits: number;
}

// --- API Functions ---

export async function getDashboard(): Promise<DashboardResponse> {
  const resp = await client.get<DashboardResponse>("/admin/dashboard");
  return resp.data;
}

export async function listAllPackages(): Promise<AdminPackageResponse[]> {
  const resp = await client.get<AdminPackageResponse[]>("/admin/packages");
  return resp.data;
}

export async function createPackage(req: PackageCreateRequest): Promise<AdminPackageResponse> {
  const resp = await client.post<AdminPackageResponse>("/admin/packages", req);
  return resp.data;
}

export async function updatePackage(
  id: number, req: PackageUpdateRequest
): Promise<AdminPackageResponse> {
  const resp = await client.put<AdminPackageResponse>(`/admin/packages/${id}`, req);
  return resp.data;
}

export async function deletePackage(id: number): Promise<void> {
  await client.delete(`/admin/packages/${id}`);
}

export async function listUsers(params?: {
  search?: string;
  page?: number;
  size?: number;
}): Promise<UserListResponse> {
  const resp = await client.get<UserListResponse>("/admin/users", { params });
  return resp.data;
}

export async function adjustCredits(
  userId: number, amount: number, remark: string
): Promise<void> {
  await client.put(`/admin/users/${userId}/credits`, { amount, remark });
}

export async function setUserStatus(
  userId: number, isActive: boolean
): Promise<void> {
  await client.put(`/admin/users/${userId}/status`, { is_active: isActive });
}

export async function getConfig(): Promise<ConfigResponse> {
  const resp = await client.get<ConfigResponse>("/admin/config");
  return resp.data;
}

export async function updateConfig(req: {
  credits_per_token?: number;
  new_user_bonus_credits?: number;
}): Promise<ConfigResponse> {
  const resp = await client.put<ConfigResponse>("/admin/config", req);
  return resp.data;
}
```

- [ ] **Step 2: 更新 auth.ts UserResponse 增加 is_admin**

在 `web/frontend/src/api/auth.ts` 的 `UserResponse` interface 中添加 `is_admin: boolean;` 字段。

- [ ] **Step 3: 更新 AppLayout.tsx 超管菜单**

在 `web/frontend/src/components/AppLayout.tsx` 中，将 `menuItems` 数组改为根据 `user?.is_admin` 动态构建：

```tsx
const menuItems = [
  { key: "/dashboard", icon: <DashboardOutlined />, label: "仪表盘" },
  { key: "/credits", icon: <CreditCardOutlined />, label: "积分" },
  { key: "/history", icon: <HistoryOutlined />, label: "历史" },
  { key: "/settings", icon: <SettingOutlined />, label: "设置" },
  ...(user?.is_admin
    ? [{ key: "/admin/dashboard", icon: <DashboardOutlined />, label: "管理" }]
    : []),
];
```

- [ ] **Step 4: 更新 App.tsx 注册 admin 路由**

在 `web/frontend/src/App.tsx` 中添加 admin 相关导入和路由：

在 imports 中添加：
```typescript
import AdminDashboard from "./pages/admin/AdminDashboard";
import AdminPackages from "./pages/admin/AdminPackages";
import AdminUsers from "./pages/admin/AdminUsers";
import AdminConfig from "./pages/admin/AdminConfig";
```

在 `ProtectedRoute` 的 Route 子元素中添加（在 Settings route 之后）：
```tsx
<Route path="/admin/dashboard" element={<AdminDashboard />} />
<Route path="/admin/packages" element={<AdminPackages />} />
<Route path="/admin/users" element={<AdminUsers />} />
<Route path="/admin/config" element={<AdminConfig />} />
```

- [ ] **Step 5: 验证 TypeScript 编译**

Run: `cd F:/dev/aigc-reducer/web/frontend && npx tsc --noEmit`

Expected: 无错误（admin 页面文件在 Task 7 创建，此处可能有 import 错误，待 Task 7 完成后验证）

- [ ] **Step 6: Commit**

```bash
git add web/frontend/src/api/admin.ts web/frontend/src/api/auth.ts web/frontend/src/components/AppLayout.tsx web/frontend/src/App.tsx
git commit -m "feat(web): add admin API client, routes, and admin menu"
```

---

## Task 7: 前端 — Admin 页面

**Files:**
- Create: `web/frontend/src/pages/admin/AdminDashboard.tsx`
- Create: `web/frontend/src/pages/admin/AdminPackages.tsx`
- Create: `web/frontend/src/pages/admin/AdminUsers.tsx`
- Create: `web/frontend/src/pages/admin/AdminConfig.tsx`

- [ ] **Step 1: 创建数据看板页面**

```tsx
// web/frontend/src/pages/admin/AdminDashboard.tsx
import { useEffect, useState } from "react";
import { Card, Col, Row, Statistic, Table, Typography } from "antd";
import {
  UserOutlined,
  DollarOutlined,
  ThunderboltOutlined,
  RiseOutlined,
} from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import {
  getDashboard,
  type DashboardResponse,
  type TopUserEntry,
} from "../../api/admin";

const { Title } = Typography;

export default function AdminDashboard() {
  const [data, setData] = useState<DashboardResponse | null>(null);

  useEffect(() => {
    getDashboard().then(setData);
  }, []);

  const topColumns: ColumnsType<TopUserEntry> = [
    { title: "用户", dataIndex: "nickname", key: "nickname" },
    { title: "手机号", dataIndex: "phone", key: "phone" },
    { title: "金额/积分", dataIndex: "amount", key: "amount" },
  ];

  return (
    <div>
      <Title level={4}>数据看板</Title>
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} md={6}>
          <Card><Statistic title="总用户" value={data?.total_users ?? 0} prefix={<UserOutlined />} /></Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card><Statistic title="总收入(元)" value={((data?.total_revenue_cents ?? 0) / 100).toFixed(2)} prefix={<DollarOutlined />} /></Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card><Statistic title="总发放积分" value={data?.total_credits_granted ?? 0} prefix={<ThunderboltOutlined />} /></Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card><Statistic title="今日新增" value={data?.today_new_users ?? 0} prefix={<RiseOutlined />} /></Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} md={12}>
          <Card title="充值 Top 10">
            <Table columns={topColumns} dataSource={data?.top_recharge_users ?? []} rowKey="user_id" size="small" pagination={false} />
          </Card>
        </Col>
        <Col xs={24} md={12}>
          <Card title="消费 Top 10">
            <Table columns={topColumns} dataSource={data?.top_consume_users ?? []} rowKey="user_id" size="small" pagination={false} />
          </Card>
        </Col>
      </Row>
    </div>
  );
}
```

- [ ] **Step 2: 创建套餐管理页面**

```tsx
// web/frontend/src/pages/admin/AdminPackages.tsx
import { useEffect, useState } from "react";
import { Button, Form, Input, InputNumber, Modal, Switch, Table, Typography, message } from "antd";
import type { ColumnsType } from "antd/es/table";
import {
  listAllPackages,
  createPackage,
  updatePackage,
  deletePackage,
  type AdminPackageResponse,
} from "../../api/admin";

const { Title } = Typography;

export default function AdminPackages() {
  const [packages, setPackages] = useState<AdminPackageResponse[]>([]);
  const [modalOpen, setModalOpen] = useState(false);
  const [editPkg, setEditPkg] = useState<AdminPackageResponse | null>(null);
  const [form] = Form.useForm();

  const fetch = () => listAllPackages().then(setPackages);

  useEffect(() => { fetch(); }, []);

  const handleSave = async () => {
    const values = await form.validateFields();
    if (editPkg) {
      await updatePackage(editPkg.id, values);
      message.success("修改成功");
    } else {
      await createPackage(values);
      message.success("创建成功");
    }
    setModalOpen(false);
    form.resetFields();
    setEditPkg(null);
    fetch();
  };

  const handleDelete = async (id: number) => {
    Modal.confirm({
      title: "确认删除？",
      onOk: async () => {
        await deletePackage(id);
        message.success("删除成功");
        fetch();
      },
    });
  };

  const openEdit = (pkg: AdminPackageResponse) => {
    setEditPkg(pkg);
    form.setFieldsValue(pkg);
    setModalOpen(true);
  };

  const openCreate = () => {
    setEditPkg(null);
    form.resetFields();
    setModalOpen(true);
  };

  const columns: ColumnsType<AdminPackageResponse> = [
    { title: "ID", dataIndex: "id", key: "id", width: 60 },
    { title: "名称", dataIndex: "name", key: "name" },
    { title: "价格(分)", dataIndex: "price_cents", key: "price_cents" },
    { title: "积分", dataIndex: "credits", key: "credits" },
    { title: "赠送", dataIndex: "bonus_credits", key: "bonus_credits" },
    { title: "排序", dataIndex: "sort_order", key: "sort_order", width: 80 },
    {
      title: "上架", dataIndex: "is_active", key: "is_active", width: 80,
      render: (v: boolean, record: AdminPackageResponse) => (
        <Switch checked={v} onChange={async (checked) => {
          await updatePackage(record.id, { is_active: checked });
          fetch();
        }} />
      ),
    },
    {
      title: "操作", key: "action", width: 140,
      render: (_: unknown, record: AdminPackageResponse) => (
        <>
          <Button type="link" size="small" onClick={() => openEdit(record)}>编辑</Button>
          <Button type="link" size="small" danger onClick={() => handleDelete(record.id)}>删除</Button>
        </>
      ),
    },
  ];

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>套餐管理</Title>
        <Button type="primary" onClick={openCreate}>新增套餐</Button>
      </div>
      <Table columns={columns} dataSource={packages} rowKey="id" />

      <Modal title={editPkg ? "编辑套餐" : "新增套餐"} open={modalOpen} onOk={handleSave} onCancel={() => { setModalOpen(false); setEditPkg(null); }}>
        <Form form={form} layout="vertical">
          <Form.Item name="name" label="名称" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="price_cents" label="价格(分)" rules={[{ required: true }]}>
            <InputNumber min={1} style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item name="credits" label="积分" rules={[{ required: true }]}>
            <InputNumber min={1} style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item name="bonus_credits" label="赠送积分" initialValue={0}>
            <InputNumber min={0} style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item name="sort_order" label="排序" initialValue={0}>
            <InputNumber min={0} style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item name="is_active" label="上架" valuePropName="checked" initialValue={true}>
            <Switch />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
```

- [ ] **Step 3: 创建用户管理页面**

```tsx
// web/frontend/src/pages/admin/AdminUsers.tsx
import { useEffect, useState } from "react";
import { Button, Input, InputNumber, Modal, Table, Tag, Typography, message } from "antd";
import type { ColumnsType } from "antd/es/table";
import { listUsers, adjustCredits, setUserStatus, type AdminUserResponse } from "../../api/admin";

const { Title } = Typography;

export default function AdminUsers() {
  const [users, setUsers] = useState<{ items: AdminUserResponse[]; total: number; page: number; size: number } | null>(null);
  const [search, setSearch] = useState("");
  const [adjustModal, setAdjustModal] = useState<{ userId: number; visible: boolean }>({ userId: 0, visible: false });
  const [adjustAmount, setAdjustAmount] = useState(0);
  const [adjustRemark, setAdjustRemark] = useState("");

  const fetch = (page = 1) => {
    listUsers({ search: search || undefined, page, size: 20 }).then(setUsers);
  };

  useEffect(() => { fetch(); }, [search]);

  const handleAdjust = async () => {
    await adjustCredits(adjustModal.userId, adjustAmount, adjustRemark || "管理员调整");
    message.success("积分调整成功");
    setAdjustModal({ userId: 0, visible: false });
    setAdjustAmount(0);
    setAdjustRemark("");
    fetch();
  };

  const handleToggleStatus = async (userId: number, isActive: boolean) => {
    Modal.confirm({
      title: `确认${isActive ? "禁用" : "启用"}该用户？`,
      onOk: async () => {
        await setUserStatus(userId, !isActive);
        message.success("操作成功");
        fetch();
      },
    });
  };

  const columns: ColumnsType<AdminUserResponse> = [
    { title: "ID", dataIndex: "id", key: "id", width: 60 },
    { title: "手机号", dataIndex: "phone", key: "phone" },
    { title: "昵称", dataIndex: "nickname", key: "nickname" },
    { title: "积分余额", dataIndex: "credit_balance", key: "credit_balance" },
    { title: "累计充值", dataIndex: "total_recharged", key: "total_recharged" },
    { title: "累计消费", dataIndex: "total_consumed", key: "total_consumed" },
    {
      title: "状态", dataIndex: "is_active", key: "is_active", width: 80,
      render: (v: boolean) => <Tag color={v ? "green" : "red"}>{v ? "正常" : "禁用"}</Tag>,
    },
    {
      title: "操作", key: "action", width: 160,
      render: (_: unknown, record: AdminUserResponse) => (
        <>
          <Button type="link" size="small" onClick={() => {
            setAdjustModal({ userId: record.id, visible: true });
          }}>调积分</Button>
          <Button type="link" size="small" danger onClick={() => handleToggleStatus(record.id, record.is_active)}>
            {record.is_active ? "禁用" : "启用"}
          </Button>
        </>
      ),
    },
  ];

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>用户管理</Title>
        <Input.Search placeholder="搜索手机号/昵称" style={{ width: 250 }} onSearch={setSearch} allowClear />
      </div>
      <Table
        columns={columns}
        dataSource={users?.items ?? []}
        rowKey="id"
        pagination={{
          current: users?.page ?? 1,
          total: users?.total ?? 0,
          pageSize: users?.size ?? 20,
          onChange: (page) => fetch(page),
        }}
      />

      <Modal title="调整积分" open={adjustModal.visible} onOk={handleAdjust} onCancel={() => setAdjustModal({ userId: 0, visible: false })}>
        <div style={{ marginBottom: 12 }}>
          <span>金额（正数加，负数减）：</span>
          <InputNumber value={adjustAmount} onChange={(v) => setAdjustAmount(v ?? 0)} style={{ width: "100%", marginTop: 8 }} />
        </div>
        <div>
          <span>备注：</span>
          <Input value={adjustRemark} onChange={(e) => setAdjustRemark(e.target.value)} placeholder="管理员调整" style={{ marginTop: 8 }} />
        </div>
      </Modal>
    </div>
  );
}
```

- [ ] **Step 4: 创建积分配置页面**

```tsx
// web/frontend/src/pages/admin/AdminConfig.tsx
import { useEffect, useState } from "react";
import { Button, Card, Form, InputNumber, message, Typography } from "antd";
import { getConfig, updateConfig, type ConfigResponse } from "../../api/admin";

const { Title } = Typography;

export default function AdminConfig() {
  const [config, setConfig] = useState<ConfigResponse | null>(null);
  const [saving, setSaving] = useState(false);
  const [form] = Form.useForm();

  useEffect(() => {
    getConfig().then((data) => {
      setConfig(data);
      form.setFieldsValue(data);
    });
  }, [form]);

  const handleSave = async () => {
    const values = await form.validateFields();
    setSaving(true);
    try {
      const updated = await updateConfig(values);
      setConfig(updated);
      message.success("配置已更新（运行时生效，重启后恢复默认）");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div>
      <Title level={4}>积分配置</Title>
      <Card style={{ maxWidth: 500 }}>
        <Form form={form} layout="vertical">
          <Form.Item name="credits_per_token" label="每 Token 积分价格" rules={[{ required: true }]}>
            <InputNumber min={0.01} step={0.1} style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item name="new_user_bonus_credits" label="新人赠送积分" rules={[{ required: true }]}>
            <InputNumber min={0} step={10} style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item>
            <Button type="primary" onClick={handleSave} loading={saving}>保存</Button>
          </Form.Item>
        </Form>
      </Card>
    </div>
  );
}
```

- [ ] **Step 5: 验证 TypeScript 编译**

Run: `cd F:/dev/aigc-reducer/web/frontend && npx tsc --noEmit`

Expected: 无错误

- [ ] **Step 6: Commit**

```bash
git add web/frontend/src/pages/admin/
git commit -m "feat(web): add admin pages (dashboard, packages, users, config)"
```

---

## Task 8: 全量回归测试

**Files:** 无新增

- [ ] **Step 1: 运行全部后端测试**

Run: `cd F:/dev/aigc-reducer/web && uv run pytest tests/ -v`

Expected: 全部 PASS

- [ ] **Step 2: 运行前端 TypeScript 检查**

Run: `cd F:/dev/aigc-reducer/web/frontend && npx tsc --noEmit`

Expected: 无错误

- [ ] **Step 3: 运行前端 lint**

Run: `cd F:/dev/aigc-reducer/web/frontend && npm run lint`

Expected: P2.5 新增文件无 error

- [ ] **Step 4: 检查 git status**

Run: `git status`

Expected: working tree clean

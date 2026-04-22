# P2: 积分充值与支付系统 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建立积分经济闭环 — 用户充值积分 → 积分用于论文检测/改写（P3），覆盖支付集成、充值套餐、积分消费引擎、交易流水和前端积分账户页面。

**Architecture:** 后端新增 3 个 ORM 模型 + 2 个服务层（credit/payment）+ 支付抽象层。积分变动在数据库事务内完成，支付回调幂等处理。前端将 Credits 占位页改造为 Tabs 容器（余额/套餐/流水）。

**Tech Stack:** FastAPI + SQLAlchemy 2.0 + Alembic + python-alipay-sdk（后端）；React 19 + TypeScript + Ant Design + Zustand（前端）

---

## File Structure

### 后端新增/修改文件

| 操作 | 路径 | 职责 |
|------|------|------|
| Modify | `web/src/aigc_web/config.py` | 新增积分和支付宝配置项 |
| Create | `web/src/aigc_web/models/recharge_package.py` | 充值套餐 ORM 模型 |
| Create | `web/src/aigc_web/models/payment_order.py` | 支付订单 ORM 模型 |
| Create | `web/src/aigc_web/models/credit_transaction.py` | 积分流水 ORM 模型 |
| Modify | `web/src/aigc_web/models/__init__.py` | 导出新模型 |
| Create | `web/src/aigc_web/schemas/credits.py` | 积分相关请求/响应 Schema |
| Create | `web/src/aigc_web/services/credit.py` | 积分服务（充值/消费/流水查询） |
| Create | `web/src/aigc_web/services/payment.py` | 支付抽象层 + 支付宝实现 + 支付服务 |
| Modify | `web/src/aigc_web/services/auth.py` | 注册流程增加新人赠送 |
| Create | `web/src/aigc_web/routers/credits.py` | 积分相关 API 路由 |
| Modify | `web/src/aigc_web/main.py` | 注册 credits 路由 |
| Create | `web/tests/test_credit_service.py` | 积分服务单元测试 |
| Create | `web/tests/test_payment_service.py` | 支付服务单元测试 |
| Create | `web/tests/test_credits_router.py` | 积分 API 集成测试 |
| Auto-gen | `web/alembic/versions/xxx_add_p2_tables.py` | 数据库迁移 |

### 前端新增/修改文件

| 操作 | 路径 | 职责 |
|------|------|------|
| Create | `web/frontend/src/api/credits.ts` | 积分 API 调用函数 |
| Create | `web/frontend/src/stores/credits.ts` | 积分 Zustand store |
| Create | `web/frontend/src/pages/credits/Balance.tsx` | 余额概览 Tab |
| Create | `web/frontend/src/pages/credits/Packages.tsx` | 套餐展示 + 充值 Tab |
| Create | `web/frontend/src/pages/credits/History.tsx` | 积分流水 Tab |
| Modify | `web/frontend/src/pages/Credits.tsx` | 改造为 Tabs 容器 |

---

## Task 1: 新增配置项

**Files:**
- Modify: `web/src/aigc_web/config.py`

- [ ] **Step 1: 在 config.py 的 Settings 类中新增配置项**

在 `CORS_ORIGINS` 字段之后、`model_config` 之前，添加：

```python
    # 积分配置
    NEW_USER_BONUS_CREDITS: int = 0
    CREDITS_PER_TOKEN: float = 1.0

    # 支付宝配置
    ALIPAY_APP_ID: str = ""
    ALIPAY_PRIVATE_KEY: str = ""
    ALIPAY_PUBLIC_KEY: str = ""
    ALIPAY_NOTIFY_URL: str = ""
    ALIPAY_RETURN_URL: str = ""
    ALIPAY_DEBUG: bool = True
```

- [ ] **Step 2: 验证配置加载正常**

Run: `cd web && uv run python -c "from aigc_web.config import settings; print(settings.NEW_USER_BONUS_CREDITS, settings.CREDITS_PER_TOKEN, settings.ALIPAY_DEBUG)"`

Expected: `0 1.0 True`

- [ ] **Step 3: Commit**

```bash
git add web/src/aigc_web/config.py
git commit -m "feat(web): add credits and alipay config settings"
```

---

## Task 2: 新增 ORM 模型 + 导出

**Files:**
- Create: `web/src/aigc_web/models/recharge_package.py`
- Create: `web/src/aigc_web/models/payment_order.py`
- Create: `web/src/aigc_web/models/credit_transaction.py`
- Modify: `web/src/aigc_web/models/__init__.py`

- [ ] **Step 1: 创建 RechargePackage 模型**

```python
# web/src/aigc_web/models/recharge_package.py
"""充值套餐 ORM 模型。"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from aigc_web.database import Base


class RechargePackage(Base):
    __tablename__ = "recharge_packages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    price_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    credits: Mapped[int] = mapped_column(Integer, nullable=False)
    bonus_credits: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)
```

- [ ] **Step 2: 创建 PaymentOrder 模型**

```python
# web/src/aigc_web/models/payment_order.py
"""支付订单 ORM 模型。"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from aigc_web.database import Base


class PaymentOrder(Base):
    __tablename__ = "payment_orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    package_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("recharge_packages.id"), nullable=False
    )
    out_trade_no: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    credits_granted: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    pay_method: Mapped[str] = mapped_column(String(20), nullable=False)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship("User")
    package: Mapped["RechargePackage"] = relationship("RechargePackage")
```

- [ ] **Step 3: 创建 CreditTransaction 模型**

```python
# web/src/aigc_web/models/credit_transaction.py
"""积分流水 ORM 模型。"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from aigc_web.database import Base


class CreditTransaction(Base):
    __tablename__ = "credit_transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    balance_after: Mapped[int] = mapped_column(Integer, nullable=False)
    ref_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    ref_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    remark: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)

    user: Mapped["User"] = relationship("User")
```

- [ ] **Step 4: 更新 models/__init__.py 导出**

将现有内容替换为：

```python
from aigc_web.models.credit_account import CreditAccount
from aigc_web.models.credit_transaction import CreditTransaction
from aigc_web.models.payment_order import PaymentOrder
from aigc_web.models.recharge_package import RechargePackage
from aigc_web.models.user import User

__all__ = ["User", "CreditAccount", "RechargePackage", "PaymentOrder", "CreditTransaction"]
```

- [ ] **Step 5: 验证模型可导入**

Run: `cd web && uv run python -c "from aigc_web.models import RechargePackage, PaymentOrder, CreditTransaction; print('OK')"`

Expected: `OK`

- [ ] **Step 6: Commit**

```bash
git add web/src/aigc_web/models/
git commit -m "feat(web): add RechargePackage, PaymentOrder, CreditTransaction models"
```

---

## Task 3: 积分服务（CreditService）

**Files:**
- Create: `web/src/aigc_web/services/credit.py`
- Create: `web/tests/test_credit_service.py`

- [ ] **Step 1: 编写积分服务测试**

```python
# web/tests/test_credit_service.py
"""积分服务单元测试。"""

import pytest

from aigc_web.models.credit_account import CreditAccount
from aigc_web.models.credit_transaction import CreditTransaction
from aigc_web.models.user import User
from aigc_web.services import credit as credit_service


def _create_user(db_session, phone="13800138000"):
    user = User(phone=phone, nickname=f"用户{phone[-4:]}")
    db_session.add(user)
    db_session.commit()
    account = CreditAccount(user_id=user.id)
    db_session.add(account)
    db_session.commit()
    return user


def test_recharge(db_session):
    user = _create_user(db_session)
    credit_service.recharge(db_session, user.id, 100, "payment_order", 1, "充值-基础包")

    account = db_session.query(CreditAccount).filter_by(user_id=user.id).one()
    assert account.balance == 100
    assert account.total_recharged == 100

    tx = db_session.query(CreditTransaction).one()
    assert tx.type == "recharge"
    assert tx.amount == 100
    assert tx.balance_after == 100
    assert tx.ref_type == "payment_order"
    assert tx.ref_id == 1
    assert tx.remark == "充值-基础包"


def test_recharge_multiple(db_session):
    user = _create_user(db_session)
    credit_service.recharge(db_session, user.id, 50, "payment_order", 1, "第一次")
    credit_service.recharge(db_session, user.id, 30, "payment_order", 2, "第二次")

    account = db_session.query(CreditAccount).filter_by(user_id=user.id).one()
    assert account.balance == 80
    assert account.total_recharged == 80

    txs = db_session.query(CreditTransaction).order_by(CreditTransaction.id).all()
    assert len(txs) == 2
    assert txs[0].balance_after == 50
    assert txs[1].balance_after == 80


def test_consume(db_session):
    user = _create_user(db_session)
    credit_service.recharge(db_session, user.id, 100, "payment_order", 1, "充值")
    credit_service.consume(db_session, user.id, 30, "detection_task", 10, "检测扣费")

    account = db_session.query(CreditAccount).filter_by(user_id=user.id).one()
    assert account.balance == 70
    assert account.total_consumed == 30

    txs = db_session.query(CreditTransaction).order_by(CreditTransaction.id).all()
    assert txs[1].type == "consume"
    assert txs[1].amount == -30
    assert txs[1].balance_after == 70
    assert txs[1].ref_type == "detection_task"
    assert txs[1].ref_id == 10


def test_consume_insufficient_balance(db_session):
    user = _create_user(db_session)
    credit_service.recharge(db_session, user.id, 50, "payment_order", 1, "充值")

    with pytest.raises(ValueError, match="积分余额不足"):
        credit_service.consume(db_session, user.id, 100, "detection_task", 1, "扣费")


def test_get_balance(db_session):
    user = _create_user(db_session)
    credit_service.recharge(db_session, user.id, 200, "payment_order", 1, "充值")
    assert credit_service.get_balance(db_session, user.id) == 200


def test_get_balance_no_account(db_session):
    assert credit_service.get_balance(db_session, 999) == 0


def test_get_transactions(db_session):
    user = _create_user(db_session)
    credit_service.recharge(db_session, user.id, 100, "payment_order", 1, "充值")
    credit_service.consume(db_session, user.id, 30, "detection_task", 1, "检测扣费")

    result = credit_service.get_transactions(db_session, user.id, page=1, size=10)
    assert result["total"] == 2
    assert len(result["items"]) == 2
    # 默认时间倒序，最新在前
    assert result["items"][0].type == "consume"


def test_get_transactions_filter_by_type(db_session):
    user = _create_user(db_session)
    credit_service.recharge(db_session, user.id, 100, "payment_order", 1, "充值")
    credit_service.consume(db_session, user.id, 30, "detection_task", 1, "检测扣费")

    result = credit_service.get_transactions(db_session, user.id, type_filter="recharge", page=1, size=10)
    assert result["total"] == 1
    assert result["items"][0].type == "recharge"


def test_get_transactions_pagination(db_session):
    user = _create_user(db_session)
    for i in range(5):
        credit_service.recharge(db_session, user.id, 10, "payment_order", i, f"充值{i}")

    result = credit_service.get_transactions(db_session, user.id, page=2, size=2)
    assert result["total"] == 5
    assert len(result["items"]) == 2
    assert result["page"] == 2


def test_grant_new_user_bonus(db_session):
    user = _create_user(db_session)
    credit_service.grant_new_user_bonus(db_session, user.id)

    account = db_session.query(CreditAccount).filter_by(user_id=user.id).one()
    assert account.balance == 0  # 默认 NEW_USER_BONUS_CREDITS=0


def test_grant_new_user_bonus_with_config(db_session, monkeypatch):
    from aigc_web import config
    monkeypatch.setattr(config.settings, "NEW_USER_BONUS_CREDITS", 50)

    user = _create_user(db_session)
    credit_service.grant_new_user_bonus(db_session, user.id)

    account = db_session.query(CreditAccount).filter_by(user_id=user.id).one()
    assert account.balance == 50
    tx = db_session.query(CreditTransaction).one()
    assert tx.remark == "新人赠送"
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd web && uv run pytest tests/test_credit_service.py -v`

Expected: FAIL — `ModuleNotFoundError: No module named 'aigc_web.services.credit'`

- [ ] **Step 3: 实现积分服务**

```python
# web/src/aigc_web/services/credit.py
"""积分服务 — 充值、消费、流水查询、新人赠送。"""

from sqlalchemy import func as sa_func
from sqlalchemy.orm import Session

from aigc_web.config import settings
from aigc_web.models.credit_account import CreditAccount
from aigc_web.models.credit_transaction import CreditTransaction


def recharge(
    db: Session,
    user_id: int,
    amount: int,
    ref_type: str | None = None,
    ref_id: int | None = None,
    remark: str | None = None,
) -> None:
    """充值积分。事务内更新余额 + 写流水。"""
    account = db.query(CreditAccount).filter_by(user_id=user_id).with_for_update().one()
    account.balance += amount
    account.total_recharged += amount

    tx = CreditTransaction(
        user_id=user_id,
        type="recharge",
        amount=amount,
        balance_after=account.balance,
        ref_type=ref_type,
        ref_id=ref_id,
        remark=remark,
    )
    db.add(tx)
    db.commit()


def consume(
    db: Session,
    user_id: int,
    token_count: int,
    ref_type: str | None = None,
    ref_id: int | None = None,
    remark: str | None = None,
) -> int:
    """消费积分。按 token_count × CREDITS_PER_TOKEN 扣减。返回消耗积分数。"""
    cost = int(token_count * settings.CREDITS_PER_TOKEN)
    account = db.query(CreditAccount).filter_by(user_id=user_id).with_for_update().one()

    if account.balance < cost:
        raise ValueError(f"积分余额不足，需要 {cost}，当前 {account.balance}")

    account.balance -= cost
    account.total_consumed += cost

    tx = CreditTransaction(
        user_id=user_id,
        type="consume",
        amount=-cost,
        balance_after=account.balance,
        ref_type=ref_type,
        ref_id=ref_id,
        remark=remark,
    )
    db.add(tx)
    db.commit()
    return cost


def get_balance(db: Session, user_id: int) -> int:
    """查询积分余额。"""
    account = db.query(CreditAccount).filter_by(user_id=user_id).first()
    return account.balance if account else 0


def get_transactions(
    db: Session,
    user_id: int,
    type_filter: str | None = None,
    page: int = 1,
    size: int = 10,
) -> dict:
    """分页查询积分流水。返回 {"items": [...], "total": int, "page": int, "size": int}。"""
    query = db.query(CreditTransaction).filter_by(user_id=user_id)
    if type_filter:
        query = query.filter(CreditTransaction.type == type_filter)

    total = query.count()
    items = (
        query.order_by(CreditTransaction.created_at.desc())
        .offset((page - 1) * size)
        .limit(size)
        .all()
    )
    return {"items": items, "total": total, "page": page, "size": size}


def grant_new_user_bonus(db: Session, user_id: int) -> None:
    """新用户注册赠送积分。配置为 0 则不赠送。"""
    bonus = settings.NEW_USER_BONUS_CREDITS
    if bonus > 0:
        recharge(db, user_id, bonus, remark="新人赠送")
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd web && uv run pytest tests/test_credit_service.py -v`

Expected: 全部 PASS

- [ ] **Step 5: Commit**

```bash
git add web/src/aigc_web/services/credit.py web/tests/test_credit_service.py
git commit -m "feat(web): add credit service with recharge, consume, transactions"
```

---

## Task 4: 支付服务（PaymentProvider + PaymentService）

**Files:**
- Create: `web/src/aigc_web/services/payment.py`
- Create: `web/tests/test_payment_service.py`

- [ ] **Step 1: 编写支付服务测试**

```python
# web/tests/test_payment_service.py
"""支付服务单元测试。"""

from unittest.mock import MagicMock, patch

import pytest

from aigc_web.models.credit_account import CreditAccount
from aigc_web.models.credit_transaction import CreditTransaction
from aigc_web.models.payment_order import PaymentOrder
from aigc_web.models.recharge_package import RechargePackage
from aigc_web.models.user import User
from aigc_web.services import payment as payment_service


def _setup_user_and_package(db_session):
    user = User(phone="13800138000", nickname="用户8000")
    db_session.add(user)
    db_session.commit()
    account = CreditAccount(user_id=user.id)
    db_session.add(account)
    db_session.commit()

    pkg = RechargePackage(
        name="基础包",
        price_cents=1000,
        credits=100,
        bonus_credits=10,
        sort_order=1,
        is_active=True,
    )
    db_session.add(pkg)
    db_session.commit()
    return user, pkg


@patch("aigc_web.services.payment.get_payment_provider")
def test_create_recharge_order(mock_get_provider, db_session):
    user, pkg = _setup_user_and_package(db_session)

    mock_provider = MagicMock()
    mock_provider.create_order.return_value = "https://pay.example.com/123"
    mock_get_provider.return_value = mock_provider

    result = payment_service.create_recharge_order(
        db_session, user.id, pkg.id, "pc_web"
    )

    assert result["order_id"] > 0
    assert result["pay_url"] == "https://pay.example.com/123"

    order = db_session.query(PaymentOrder).one()
    assert order.user_id == user.id
    assert order.package_id == pkg.id
    assert order.amount_cents == 1000
    assert order.credits_granted == 110  # 100 + 10 bonus
    assert order.status == "pending"
    assert order.pay_method == "pc_web"
    assert order.out_trade_no.startswith("PAY")


@patch("aigc_web.services.payment.get_payment_provider")
def test_create_recharge_order_inactive_package(mock_get_provider, db_session):
    user, pkg = _setup_user_and_package(db_session)
    pkg.is_active = False
    db_session.commit()

    with pytest.raises(ValueError, match="套餐不存在或已下架"):
        payment_service.create_recharge_order(db_session, user.id, pkg.id, "pc_web")


def test_handle_payment_callback_paid(db_session):
    user, pkg = _setup_user_and_package(db_session)

    order = PaymentOrder(
        user_id=user.id,
        package_id=pkg.id,
        out_trade_no="PAY_TEST_001",
        amount_cents=1000,
        credits_granted=110,
        status="pending",
        pay_method="pc_web",
    )
    db_session.add(order)
    db_session.commit()

    payment_service.handle_payment_callback(db_session, order.id)

    db_session.refresh(order)
    assert order.status == "paid"
    assert order.paid_at is not None

    account = db_session.query(CreditAccount).filter_by(user_id=user.id).one()
    assert account.balance == 110
    assert account.total_recharged == 110

    tx = db_session.query(CreditTransaction).one()
    assert tx.amount == 110
    assert tx.balance_after == 110
    assert tx.ref_type == "payment_order"
    assert tx.ref_id == order.id


def test_handle_payment_callback_idempotent(db_session):
    user, pkg = _setup_user_and_package(db_session)

    order = PaymentOrder(
        user_id=user.id,
        package_id=pkg.id,
        out_trade_no="PAY_TEST_002",
        amount_cents=1000,
        credits_granted=110,
        status="pending",
        pay_method="pc_web",
    )
    db_session.add(order)
    db_session.commit()

    # 第一次回调
    payment_service.handle_payment_callback(db_session, order.id)
    # 第二次回调（幂等）
    payment_service.handle_payment_callback(db_session, order.id)

    txs = db_session.query(CreditTransaction).all()
    assert len(txs) == 1  # 不重复加积分


def test_query_order_status(db_session):
    user, pkg = _setup_user_and_package(db_session)

    order = PaymentOrder(
        user_id=user.id,
        package_id=pkg.id,
        out_trade_no="PAY_TEST_003",
        amount_cents=1000,
        credits_granted=110,
        status="pending",
        pay_method="pc_web",
    )
    db_session.add(order)
    db_session.commit()

    result = payment_service.query_order_status(db_session, order.id, user.id)
    assert result["status"] == "pending"
    assert result["credits_granted"] == 110


def test_query_order_status_wrong_user(db_session):
    user, pkg = _setup_user_and_package(db_session)
    other_user = User(phone="13800138999", nickname="其他用户")
    db_session.add(other_user)
    db_session.commit()

    order = PaymentOrder(
        user_id=user.id,
        package_id=pkg.id,
        out_trade_no="PAY_TEST_004",
        amount_cents=1000,
        credits_granted=110,
        status="pending",
        pay_method="pc_web",
    )
    db_session.add(order)
    db_session.commit()

    with pytest.raises(ValueError, match="订单不存在"):
        payment_service.query_order_status(db_session, order.id, other_user.id)
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd web && uv run pytest tests/test_payment_service.py -v`

Expected: FAIL — `ModuleNotFoundError: No module named 'aigc_web.services.payment'`

- [ ] **Step 3: 实现支付服务**

```python
# web/src/aigc_web/services/payment.py
"""支付服务 — 支付抽象层 + 支付宝实现 + 订单管理。"""

import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from aigc_web.config import settings
from aigc_web.models.payment_order import PaymentOrder
from aigc_web.models.recharge_package import RechargePackage
from aigc_web.services import credit as credit_service


class PaymentProvider(ABC):
    """支付渠道抽象基类。"""

    @abstractmethod
    def create_order(
        self,
        out_trade_no: str,
        amount: int,
        subject: str,
        return_url: str,
        notify_url: str,
        pay_method: str,
    ) -> str:
        """创建支付订单，返回支付链接。"""

    @abstractmethod
    def verify_callback(self, params: dict) -> bool:
        """验证回调签名。"""


class AlipayProvider(PaymentProvider):
    """支付宝支付实现。基于 python-alipay-sdk。"""

    def __init__(self) -> None:
        self._alipay = None

    def _get_alipay(self):
        if self._alipay is None:
            from alipay import AliPay

            self._alipay = AliPay(
                appid=settings.ALIPAY_APP_ID,
                app_private_key_string=settings.ALIPAY_PRIVATE_KEY,
                alipay_public_key_string=settings.ALIPAY_PUBLIC_KEY,
                sign_type="RSA2",
                debug=settings.ALIPAY_DEBUG,
            )
        return self._alipay

    def create_order(
        self,
        out_trade_no: str,
        amount: int,
        subject: str,
        return_url: str,
        notify_url: str,
        pay_method: str,
    ) -> str:
        alipay = self._get_alipay()
        amount_yuan = amount / 100  # 分转元

        if pay_method == "h5":
            order_string = alipay.api_alipay_trade_wap_pay(
                out_trade_no=out_trade_no,
                total_amount=str(amount_yuan),
                subject=subject,
                return_url=return_url,
                notify_url=notify_url,
            )
        else:
            order_string = alipay.api_alipay_trade_page_pay(
                out_trade_no=out_trade_no,
                total_amount=str(amount_yuan),
                subject=subject,
                return_url=return_url,
                notify_url=notify_url,
            )
        return "https://openapi.alipay.com/gateway.do?" + order_string

    def verify_callback(self, params: dict) -> bool:
        alipay = self._get_alipay()
        return alipay.verify(params, params.get("sign"))


class MockPaymentProvider(PaymentProvider):
    """开发环境模拟支付渠道。"""

    def create_order(
        self,
        out_trade_no: str,
        amount: int,
        subject: str,
        return_url: str,
        notify_url: str,
        pay_method: str,
    ) -> str:
        return f"https://mock-pay.example.com/pay?order={out_trade_no}&amount={amount}"

    def verify_callback(self, params: dict) -> bool:
        return True


_payment_provider: PaymentProvider | None = None


def get_payment_provider() -> PaymentProvider:
    """获取支付渠道实例（单例）。"""
    global _payment_provider
    if _payment_provider is None:
        if settings.ALIPAY_APP_ID:
            _payment_provider = AlipayProvider()
        else:
            _payment_provider = MockPaymentProvider()
    return _payment_provider


def set_payment_provider(provider: PaymentProvider) -> None:
    """测试用：注入自定义支付渠道。"""
    global _payment_provider
    _payment_provider = provider


def _generate_trade_no() -> str:
    """生成唯一商户订单号。"""
    return f"PAY_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}"


def create_recharge_order(
    db: Session,
    user_id: int,
    package_id: int,
    pay_method: str,
) -> dict:
    """创建充值订单，返回 {"order_id": int, "pay_url": str}。"""
    pkg = db.query(RechargePackage).filter_by(id=package_id, is_active=True).first()
    if pkg is None:
        raise ValueError("套餐不存在或已下架")

    out_trade_no = _generate_trade_no()
    credits_granted = pkg.credits + pkg.bonus_credits

    order = PaymentOrder(
        user_id=user_id,
        package_id=pkg.id,
        out_trade_no=out_trade_no,
        amount_cents=pkg.price_cents,
        credits_granted=credits_granted,
        status="pending",
        pay_method=pay_method,
    )
    db.add(order)
    db.commit()
    db.refresh(order)

    provider = get_payment_provider()
    pay_url = provider.create_order(
        out_trade_no=out_trade_no,
        amount=pkg.price_cents,
        subject=f"积分充值-{pkg.name}",
        return_url=settings.ALIPAY_RETURN_URL,
        notify_url=settings.ALIPAY_NOTIFY_URL,
        pay_method=pay_method,
    )

    return {"order_id": order.id, "pay_url": pay_url}


def handle_payment_callback(db: Session, order_id: int) -> None:
    """处理支付成功回调。幂等：已 paid 的订单不重复加积分。"""
    order = db.query(PaymentOrder).filter_by(id=order_id).one()
    if order.status == "paid":
        return  # 幂等保护

    order.status = "paid"
    order.paid_at = datetime.now(timezone.utc)
    db.commit()

    credit_service.recharge(
        db,
        user_id=order.user_id,
        amount=order.credits_granted,
        ref_type="payment_order",
        ref_id=order.id,
        remark=f"充值-{order.out_trade_no}",
    )


def query_order_status(db: Session, order_id: int, user_id: int) -> dict:
    """查询订单状态，校验归属当前用户。"""
    order = db.query(PaymentOrder).filter_by(id=order_id, user_id=user_id).first()
    if order is None:
        raise ValueError("订单不存在")

    return {
        "id": order.id,
        "out_trade_no": order.out_trade_no,
        "amount_cents": order.amount_cents,
        "credits_granted": order.credits_granted,
        "status": order.status,
        "pay_method": order.pay_method,
        "created_at": order.created_at,
        "paid_at": order.paid_at,
    }
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd web && uv run pytest tests/test_payment_service.py -v`

Expected: 全部 PASS

- [ ] **Step 5: Commit**

```bash
git add web/src/aigc_web/services/payment.py web/tests/test_payment_service.py
git commit -m "feat(web): add payment service with provider abstraction and alipay"
```

---

## Task 5: 更新注册流程（新人赠送）

**Files:**
- Modify: `web/src/aigc_web/services/auth.py`
- Modify: `web/tests/test_auth_service.py`

- [ ] **Step 1: 编写新人赠送测试**

在 `web/tests/test_auth_service.py` 末尾追加：

```python
def test_login_grants_new_user_bonus(db_session, monkeypatch):
    from aigc_web import config
    monkeypatch.setattr(config.settings, "NEW_USER_BONUS_CREDITS", 50)

    from aigc_web.models.credit_account import CreditAccount
    result = auth_service.login_or_register(db_session, phone="13800138099")
    account = db_session.query(CreditAccount).filter_by(user_id=result.user.id).one()
    assert account.balance == 50
    assert result.user.credit_balance == 50
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd web && uv run pytest tests/test_auth_service.py::test_login_grants_new_user_bonus -v`

Expected: FAIL — 断言 balance == 50（实际为 0）

- [ ] **Step 3: 修改 auth.py 注册流程**

在 `web/src/aigc_web/services/auth.py` 中添加导入和方法调用。

在文件顶部 imports 末尾添加：

```python
from aigc_web.services import credit as credit_service
```

在 `login_or_register` 函数中，`db.add(account)` 和 `db.commit()` 之后（约第 25-27 行），插入新人赠送调用。将注册部分改为：

```python
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

        # 新人赠送积分
        credit_service.grant_new_user_bonus(db, user.id)
```

注意：`account` 变量在 `db.commit()` 之后需要重新查询以获取最新余额。将下方获取余额的代码改为：

```python
    # 获取积分余额（新人赠送后需重新查询）
    account = db.query(CreditAccount).filter(CreditAccount.user_id == user.id).first()
    balance = account.balance if account else 0
```

这段代码已存在，无需改动（只是注释更新，确保逻辑正确）。

- [ ] **Step 4: 运行全部 auth 测试确认通过**

Run: `cd web && uv run pytest tests/test_auth_service.py -v`

Expected: 全部 PASS（包括新测试和原有测试）

- [ ] **Step 5: Commit**

```bash
git add web/src/aigc_web/services/auth.py web/tests/test_auth_service.py
git commit -m "feat(web): grant new user bonus on registration"
```

---

## Task 6: 积分 Schema

**Files:**
- Create: `web/src/aigc_web/schemas/credits.py`

- [ ] **Step 1: 创建积分相关 Schema**

```python
# web/src/aigc_web/schemas/credits.py
"""积分相关的请求/响应模型。"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


# --- 套餐 ---

class PackageResponse(BaseModel):
    id: int
    name: str
    price_cents: int
    credits: int
    bonus_credits: int

    model_config = {"from_attributes": True}


# --- 充值 ---

class RechargeRequest(BaseModel):
    package_id: int
    pay_method: Literal["pc_web", "h5"]


class RechargeResponse(BaseModel):
    order_id: int
    pay_url: str


# --- 订单 ---

class OrderResponse(BaseModel):
    id: int
    out_trade_no: str
    amount_cents: int
    credits_granted: int
    status: str
    pay_method: str
    created_at: datetime
    paid_at: datetime | None


# --- 流水 ---

class TransactionResponse(BaseModel):
    id: int
    type: str
    amount: int
    balance_after: int
    remark: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class TransactionListResponse(BaseModel):
    items: list[TransactionResponse]
    total: int
    page: int
    size: int


# --- 余额 ---

class BalanceResponse(BaseModel):
    balance: int
    total_recharged: int
    total_consumed: int
```

- [ ] **Step 2: 验证 Schema 可导入**

Run: `cd web && uv run python -c "from aigc_web.schemas.credits import RechargeRequest, PackageResponse; print('OK')"`

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add web/src/aigc_web/schemas/credits.py
git commit -m "feat(web): add credits request/response schemas"
```

---

## Task 7: 积分 API 路由

**Files:**
- Create: `web/src/aigc_web/routers/credits.py`
- Modify: `web/src/aigc_web/main.py`
- Create: `web/tests/test_credits_router.py`

- [ ] **Step 1: 创建积分路由**

```python
# web/src/aigc_web/routers/credits.py
"""积分相关 API 路由。"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from aigc_web.database import get_db
from aigc_web.dependencies import require_current_user
from aigc_web.models.credit_account import CreditAccount
from aigc_web.models.payment_order import PaymentOrder
from aigc_web.models.recharge_package import RechargePackage
from aigc_web.models.user import User
from aigc_web.schemas.auth import MessageResponse
from aigc_web.schemas.credits import (
    BalanceResponse,
    OrderResponse,
    PackageResponse,
    RechargeRequest,
    RechargeResponse,
    TransactionListResponse,
)
from aigc_web.services import credit as credit_service
from aigc_web.services import payment as payment_service

router = APIRouter(prefix="/api/credits", tags=["credits"])


@router.get("/packages", response_model=list[PackageResponse])
def list_packages(db: Session = Depends(get_db)):
    pkgs = (
        db.query(RechargePackage)
        .filter(RechargePackage.is_active == True)
        .order_by(RechargePackage.sort_order)
        .all()
    )
    return pkgs


@router.post("/recharge", response_model=RechargeResponse)
def create_recharge(
    req: RechargeRequest,
    user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
):
    try:
        return payment_service.create_recharge_order(db, user.id, req.package_id, req.pay_method)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e


@router.get("/orders/{order_id}", response_model=OrderResponse)
def get_order(
    order_id: int,
    user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
):
    try:
        return payment_service.query_order_status(db, order_id, user.id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
        ) from e


@router.post("/payment/callback")
async def payment_callback(request: Request, db: Session = Depends(get_db)):
    """支付宝异步回调通知。验签 → 幂等 → 到账。"""
    form = await request.form()
    params = dict(form)

    provider = payment_service.get_payment_provider()
    if not provider.verify_callback(params):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="验签失败"
        )

    out_trade_no = params.get("out_trade_no")
    order = (
        db.query(PaymentOrder)
        .filter_by(out_trade_no=out_trade_no)
        .first()
    )
    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="订单不存在"
        )

    payment_service.handle_payment_callback(db, order.id)
    return MessageResponse(message="success")


@router.get("/transactions", response_model=TransactionListResponse)
def list_transactions(
    type: str | None = None,
    page: int = 1,
    size: int = 10,
    user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
):
    result = credit_service.get_transactions(db, user.id, type_filter=type, page=page, size=size)
    return TransactionListResponse(
        items=[
            {
                "id": tx.id,
                "type": tx.type,
                "amount": tx.amount,
                "balance_after": tx.balance_after,
                "remark": tx.remark,
                "created_at": tx.created_at,
            }
            for tx in result["items"]
        ],
        total=result["total"],
        page=result["page"],
        size=result["size"],
    )


@router.get("/balance", response_model=BalanceResponse)
def get_balance(
    user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
):
    account = db.query(CreditAccount).filter_by(user_id=user.id).first()
    if account is None:
        return BalanceResponse(balance=0, total_recharged=0, total_consumed=0)
    return BalanceResponse(
        balance=account.balance,
        total_recharged=account.total_recharged,
        total_consumed=account.total_consumed,
    )
```

- [ ] **Step 2: 在 main.py 注册路由**

在 `web/src/aigc_web/main.py` 中添加导入和注册。

在 import 区域添加：

```python
from aigc_web.routers import credits as credits_router
```

在 `app.include_router(auth_router.router)` 之后添加：

```python
app.include_router(credits_router.router)
```

- [ ] **Step 3: 编写路由集成测试**

```python
# web/tests/test_credits_router.py
"""积分 API 集成测试。"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from aigc_web.database import Base, get_db
from aigc_web.dependencies import set_verification_service
from aigc_web.main import app
from aigc_web.models.credit_account import CreditAccount
from aigc_web.models.payment_order import PaymentOrder
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


def _create_user_and_login():
    db = _db()
    user = User(phone="13800138000", nickname="测试用户")
    db.add(user)
    db.commit()
    account = CreditAccount(user_id=user.id)
    db.add(account)
    db.commit()
    token = create_access_token(user.id)
    return token, user.id


def _seed_package():
    db = _db()
    pkg = RechargePackage(
        name="基础包",
        price_cents=1000,
        credits=100,
        bonus_credits=10,
        sort_order=1,
        is_active=True,
    )
    db.add(pkg)
    db.commit()
    return pkg.id


def test_list_packages(client):
    _seed_package()
    token, _ = _create_user_and_login()

    resp = client.get("/api/credits/packages", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["name"] == "基础包"
    assert data[0]["price_cents"] == 1000


def test_get_balance(client):
    token, _ = _create_user_and_login()

    resp = client.get("/api/credits/balance", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["balance"] == 0
    assert data["total_recharged"] == 0


def test_create_recharge_order(client):
    pkg_id = _seed_package()
    token, _ = _create_user_and_login()

    resp = client.post(
        "/api/credits/recharge",
        json={"package_id": pkg_id, "pay_method": "pc_web"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "order_id" in data
    assert "pay_url" in data


def test_get_order_status(client):
    pkg_id = _seed_package()
    token, _ = _create_user_and_login()

    create_resp = client.post(
        "/api/credits/recharge",
        json={"package_id": pkg_id, "pay_method": "pc_web"},
        headers={"Authorization": f"Bearer {token}"},
    )
    order_id = create_resp.json()["order_id"]

    resp = client.get(
        f"/api/credits/orders/{order_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "pending"


def test_payment_callback(client):
    """测试支付回调端点（MockPaymentProvider 验签总通过）。"""
    db = _db()
    user = User(phone="13800138100", nickname="回调用户")
    db.add(user)
    db.commit()
    account = CreditAccount(user_id=user.id)
    db.add(account)
    db.commit()

    pkg = RechargePackage(
        name="回调测试包", price_cents=500, credits=50, bonus_credits=0,
        sort_order=1, is_active=True,
    )
    db.add(pkg)
    db.commit()

    order = PaymentOrder(
        user_id=user.id,
        package_id=pkg.id,
        out_trade_no="PAY_CALLBACK_TEST",
        amount_cents=500,
        credits_granted=50,
        status="pending",
        pay_method="pc_web",
    )
    db.add(order)
    db.commit()

    resp = client.post(
        "/api/credits/payment/callback",
        data={"out_trade_no": "PAY_CALLBACK_TEST"},
    )
    assert resp.status_code == 200
    assert resp.json()["message"] == "success"

    # 验证余额已更新
    db.refresh(account)
    assert account.balance == 50


def test_payment_callback_idempotent(client):
    """回调幂等：重复回调不重复加积分。"""
    db = _db()
    user = User(phone="13800138101", nickname="幂等用户")
    db.add(user)
    db.commit()
    account = CreditAccount(user_id=user.id)
    db.add(account)
    db.commit()

    pkg = RechargePackage(
        name="幂等测试包", price_cents=500, credits=50, bonus_credits=0,
        sort_order=1, is_active=True,
    )
    db.add(pkg)
    db.commit()

    order = PaymentOrder(
        user_id=user.id,
        package_id=pkg.id,
        out_trade_no="PAY_IDEMPOTENT_TEST",
        amount_cents=500,
        credits_granted=50,
        status="pending",
        pay_method="pc_web",
    )
    db.add(order)
    db.commit()

    # 第一次回调
    client.post("/api/credits/payment/callback", data={"out_trade_no": "PAY_IDEMPOTENT_TEST"})
    # 第二次回调
    resp = client.post("/api/credits/payment/callback", data={"out_trade_no": "PAY_IDEMPOTENT_TEST"})
    assert resp.status_code == 200

    db.refresh(account)
    assert account.balance == 50  # 不重复加


def test_get_transactions(client):
    token, _ = _create_user_and_login()

    resp = client.get(
        "/api/credits/transactions",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["total"] == 0


def test_unauthorized_access(client):
    resp = client.get("/api/credits/balance")
    assert resp.status_code == 401
```

- [ ] **Step 4: 运行路由测试**

Run: `cd web && uv run pytest tests/test_credits_router.py -v`

Expected: 全部 PASS

- [ ] **Step 5: 运行全部后端测试确认无回归**

Run: `cd web && uv run pytest tests/ -v`

Expected: 全部 PASS

- [ ] **Step 6: Commit**

```bash
git add web/src/aigc_web/routers/credits.py web/src/aigc_web/main.py web/tests/test_credits_router.py
git commit -m "feat(web): add credits API routes with integration tests"
```

---

## Task 8: 数据库迁移

**Files:**
- Auto-gen: `web/alembic/versions/xxx_add_p2_tables.py`
- Modify: `web/alembic/env.py`

- [ ] **Step 1: 更新 alembic env.py 导入新模型**

在 `web/alembic/env.py` 中，将 model import 行改为：

```python
from aigc_web.models import credit_account, credit_transaction, payment_order, recharge_package, user  # noqa: F401
```

- [ ] **Step 2: 生成迁移脚本**

Run: `cd web && uv run alembic revision --autogenerate -m "add recharge_packages payment_orders credit_transactions"`

Expected: 生成新的迁移文件，包含 3 个 `create_table` 操作

- [ ] **Step 3: 验证迁移脚本内容**

打开生成的迁移文件，确认包含：
- `create_table('recharge_packages', ...)`
- `create_table('payment_orders', ...)` 包含外键
- `create_table('credit_transactions', ...)` 包含外键

- [ ] **Step 4: 执行迁移（如使用 SQLite 开发库）**

Run: `cd web && uv run alembic upgrade head`

Expected: 无报错

- [ ] **Step 5: Commit**

```bash
git add web/alembic/
git commit -m "feat(web): add alembic migration for P2 tables"
```

---

## Task 9: 添加 python-alipay-sdk 依赖

**Files:**
- Modify: `web/pyproject.toml`

- [ ] **Step 1: 添加依赖**

在 `web/pyproject.toml` 的 `dependencies` 列表中添加 `"python-alipay-sdk>=3.5"`。

- [ ] **Step 2: 安装依赖**

Run: `cd web && uv sync`

Expected: 成功安装

- [ ] **Step 3: Commit**

```bash
git add web/pyproject.toml web/uv.lock
git commit -m "feat(web): add python-alipay-sdk dependency"
```

---

## Task 10: 前端 — 积分 API 客户端

**Files:**
- Create: `web/frontend/src/api/credits.ts`

- [ ] **Step 1: 创建积分 API 调用函数**

```typescript
// web/frontend/src/api/credits.ts
import client from "./client";

// --- Types ---

export interface PackageResponse {
  id: number;
  name: string;
  price_cents: number;
  credits: number;
  bonus_credits: number;
}

export interface BalanceResponse {
  balance: number;
  total_recharged: number;
  total_consumed: number;
}

export interface RechargeRequest {
  package_id: number;
  pay_method: "pc_web" | "h5";
}

export interface RechargeResponse {
  order_id: number;
  pay_url: string;
}

export interface OrderResponse {
  id: number;
  out_trade_no: string;
  amount_cents: number;
  credits_granted: number;
  status: string;
  pay_method: string;
  created_at: string;
  paid_at: string | null;
}

export interface TransactionResponse {
  id: number;
  type: string;
  amount: number;
  balance_after: number;
  remark: string | null;
  created_at: string;
}

export interface TransactionListResponse {
  items: TransactionResponse[];
  total: number;
  page: number;
  size: number;
}

// --- API Functions ---

export async function getPackages(): Promise<PackageResponse[]> {
  const resp = await client.get<PackageResponse[]>("/credits/packages");
  return resp.data;
}

export async function getBalance(): Promise<BalanceResponse> {
  const resp = await client.get<BalanceResponse>("/credits/balance");
  return resp.data;
}

export async function createRecharge(
  req: RechargeRequest
): Promise<RechargeResponse> {
  const resp = await client.post<RechargeResponse>("/credits/recharge", req);
  return resp.data;
}

export async function getOrder(orderId: number): Promise<OrderResponse> {
  const resp = await client.get<OrderResponse>(`/credits/orders/${orderId}`);
  return resp.data;
}

export async function getTransactions(params?: {
  type?: string;
  page?: number;
  size?: number;
}): Promise<TransactionListResponse> {
  const resp = await client.get<TransactionListResponse>(
    "/credits/transactions",
    { params }
  );
  return resp.data;
}
```

- [ ] **Step 2: 验证 TypeScript 编译**

Run: `cd web/frontend && npx tsc --noEmit`

Expected: 无错误

- [ ] **Step 3: Commit**

```bash
git add web/frontend/src/api/credits.ts
git commit -m "feat(web): add credits API client"
```

---

## Task 11: 前端 — 积分 Zustand Store

**Files:**
- Create: `web/frontend/src/stores/credits.ts`

- [ ] **Step 1: 创建积分 store**

```typescript
// web/frontend/src/stores/credits.ts
import { create } from "zustand";
import {
  getBalance,
  getPackages,
  getTransactions,
  type BalanceResponse,
  type PackageResponse,
  type TransactionListResponse,
} from "../api/credits";

interface CreditsState {
  balance: BalanceResponse | null;
  packages: PackageResponse[];
  transactions: TransactionListResponse | null;
  loading: boolean;
  fetchBalance: () => Promise<void>;
  fetchPackages: () => Promise<void>;
  fetchTransactions: (params?: {
    type?: string;
    page?: number;
    size?: number;
  }) => Promise<void>;
}

export const useCreditsStore = create<CreditsState>((set) => ({
  balance: null,
  packages: [],
  transactions: null,
  loading: false,

  fetchBalance: async () => {
    const balance = await getBalance();
    set({ balance });
  },

  fetchPackages: async () => {
    const packages = await getPackages();
    set({ packages });
  },

  fetchTransactions: async (params) => {
    set({ loading: true });
    try {
      const transactions = await getTransactions(params);
      set({ transactions, loading: false });
    } catch {
      set({ loading: false });
    }
  },
}));
```

- [ ] **Step 2: 验证 TypeScript 编译**

Run: `cd web/frontend && npx tsc --noEmit`

Expected: 无错误

- [ ] **Step 3: Commit**

```bash
git add web/frontend/src/stores/credits.ts
git commit -m "feat(web): add credits Zustand store"
```

---

## Task 12: 前端 — 积分页面（Balance + Packages + History + Tabs 容器）

**Files:**
- Create: `web/frontend/src/pages/credits/Balance.tsx`
- Create: `web/frontend/src/pages/credits/Packages.tsx`
- Create: `web/frontend/src/pages/credits/History.tsx`
- Modify: `web/frontend/src/pages/Credits.tsx`

- [ ] **Step 1: 创建 Balance 余额概览组件**

```tsx
// web/frontend/src/pages/credits/Balance.tsx
import { useEffect } from "react";
import { Card, Col, Row, Statistic, Button, Typography, List } from "antd";
import { CreditCardOutlined } from "@ant-design/icons";
import { useCreditsStore } from "../../stores/credits";

const { Text } = Typography;

interface BalanceProps {
  onGoPackages: () => void;
}

export default function Balance({ onGoPackages }: BalanceProps) {
  const { balance, transactions, fetchBalance, fetchTransactions } =
    useCreditsStore();

  useEffect(() => {
    fetchBalance();
    fetchTransactions({ page: 1, size: 5 });
  }, [fetchBalance, fetchTransactions]);

  return (
    <div>
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={8}>
          <Card>
            <Statistic
              title="当前积分"
              value={balance?.balance ?? 0}
              prefix={<CreditCardOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card>
            <Statistic title="累计充值" value={balance?.total_recharged ?? 0} />
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card>
            <Statistic title="累计消费" value={balance?.total_consumed ?? 0} />
          </Card>
        </Col>
      </Row>

      <Card
        title="最近流水"
        style={{ marginTop: 16 }}
        extra={
          <Button type="link" onClick={onGoPackages}>
            充值积分
          </Button>
        }
      >
        {transactions && transactions.items.length > 0 ? (
          <List
            size="small"
            dataSource={transactions.items.slice(0, 5)}
            renderItem={(item) => (
              <List.Item>
                <List.Item.Meta
                  title={item.remark || (item.type === "recharge" ? "充值" : "消费")}
                  description={item.created_at}
                />
                <Text type={item.amount > 0 ? "success" : "danger"}>
                  {item.amount > 0 ? "+" : ""}
                  {item.amount}
                </Text>
              </List.Item>
            )}
          />
        ) : (
          <Text type="secondary">暂无流水记录</Text>
        )}
      </Card>
    </div>
  );
}
```

- [ ] **Step 2: 创建 Packages 套餐组件**

```tsx
// web/frontend/src/pages/credits/Packages.tsx
import { useEffect, useState } from "react";
import {
  Card,
  Row,
  Col,
  Button,
  Typography,
  Tag,
  Modal,
  message,
} from "antd";
import { useCreditsStore } from "../../stores/credits";
import { createRecharge } from "../../api/credits";

const { Title, Text } = Typography;

export default function Packages() {
  const { packages, fetchPackages, fetchBalance } = useCreditsStore();
  const [payingOrderId, setPayingOrderId] = useState<number | null>(null);
  const [polling, setPolling] = useState(false);

  useEffect(() => {
    fetchPackages();
  }, [fetchPackages]);

  const handleRecharge = async (pkgId: number, pkgName: string, price: number) => {
    Modal.confirm({
      title: "确认充值",
      content: `套餐：${pkgName}，金额：¥${(price / 100).toFixed(2)}`,
      onOk: async () => {
        try {
          const result = await createRecharge({
            package_id: pkgId,
            pay_method: "pc_web",
          });
          setPayingOrderId(result.order_id);
          window.location.href = result.pay_url;
          startPolling(result.order_id);
        } catch {
          message.error("创建订单失败");
        }
      },
    });
  };

  const startPolling = (orderId: number) => {
    setPolling(true);
    let count = 0;
    const interval = setInterval(async () => {
      count++;
      if (count > 30) {
        clearInterval(interval);
        setPolling(false);
        return;
      }
      try {
        const { getOrder } = await import("../../api/credits");
        const order = await getOrder(orderId);
        if (order.status === "paid") {
          clearInterval(interval);
          setPolling(false);
          setPayingOrderId(null);
          message.success("充值成功！");
          fetchBalance();
        }
      } catch {
        // 继续轮询
      }
    }, 2000);
  };

  return (
    <div>
      <Title level={5}>选择充值套餐</Title>
      <Row gutter={[16, 16]}>
        {packages.map((pkg) => (
          <Col xs={24} sm={12} md={8} key={pkg.id}>
            <Card hoverable>
              <Title level={4} style={{ textAlign: "center" }}>
                {pkg.name}
              </Title>
              <div style={{ textAlign: "center", margin: "16px 0" }}>
                <Text style={{ fontSize: 32, fontWeight: "bold" }}>
                  ¥{(pkg.price_cents / 100).toFixed(0)}
                </Text>
              </div>
              <div style={{ textAlign: "center", marginBottom: 8 }}>
                <Text>{pkg.credits} 积分</Text>
                {pkg.bonus_credits > 0 && (
                  <Tag color="red" style={{ marginLeft: 8 }}>
                    赠送 {pkg.bonus_credits}
                  </Tag>
                )}
              </div>
              <Button
                type="primary"
                block
                loading={polling && payingOrderId !== null}
                onClick={() =>
                  handleRecharge(pkg.id, pkg.name, pkg.price_cents)
                }
              >
                立即充值
              </Button>
            </Card>
          </Col>
        ))}
      </Row>
      {packages.length === 0 && (
        <Card>
          <Text type="secondary">暂无可用套餐</Text>
        </Card>
      )}
    </div>
  );
}
```

- [ ] **Step 3: 创建 History 积分流水组件**

```tsx
// web/frontend/src/pages/credits/History.tsx
import { useEffect, useState } from "react";
import { Table, Tag, Select, Typography } from "antd";
import type { ColumnsType } from "antd/es/table";
import { useCreditsStore } from "../../stores/credits";
import type { TransactionResponse } from "../../api/credits";

const { Title } = Typography;

export default function History() {
  const { transactions, fetchTransactions, loading } = useCreditsStore();
  const [typeFilter, setTypeFilter] = useState<string | undefined>(undefined);

  useEffect(() => {
    fetchTransactions({ type: typeFilter, page: 1, size: 10 });
  }, [typeFilter, fetchTransactions]);

  const columns: ColumnsType<TransactionResponse> = [
    {
      title: "时间",
      dataIndex: "created_at",
      key: "created_at",
      render: (v: string) => new Date(v).toLocaleString("zh-CN"),
    },
    {
      title: "类型",
      dataIndex: "type",
      key: "type",
      render: (v: string) => (
        <Tag color={v === "recharge" ? "green" : "red"}>
          {v === "recharge" ? "充值" : "消费"}
        </Tag>
      ),
    },
    {
      title: "积分变动",
      dataIndex: "amount",
      key: "amount",
      render: (v: number) => (
        <span style={{ color: v > 0 ? "#52c41a" : "#ff4d4f" }}>
          {v > 0 ? "+" : ""}
          {v}
        </span>
      ),
    },
    {
      title: "余额",
      dataIndex: "balance_after",
      key: "balance_after",
    },
    {
      title: "备注",
      dataIndex: "remark",
      key: "remark",
    },
  ];

  return (
    <div>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: 16,
        }}
      >
        <Title level={5} style={{ margin: 0 }}>
          积分流水
        </Title>
        <Select
          style={{ width: 120 }}
          placeholder="全部类型"
          allowClear
          onChange={(v) => setTypeFilter(v)}
          options={[
            { label: "充值", value: "recharge" },
            { label: "消费", value: "consume" },
          ]}
        />
      </div>
      <Table
        columns={columns}
        dataSource={transactions?.items ?? []}
        rowKey="id"
        loading={loading}
        pagination={{
          current: transactions?.page ?? 1,
          total: transactions?.total ?? 0,
          pageSize: transactions?.size ?? 10,
          onChange: (page) =>
            fetchTransactions({ type: typeFilter, page, size: 10 }),
        }}
      />
    </div>
  );
}
```

- [ ] **Step 4: 改造 Credits.tsx 为 Tabs 容器**

将 `web/frontend/src/pages/Credits.tsx` 替换为：

```tsx
// web/frontend/src/pages/Credits.tsx
import { useRef } from "react";
import { Typography, Tabs } from "antd";
import Balance from "./credits/Balance";
import Packages from "./credits/Packages";
import History from "./credits/History";

const { Title } = Typography;

export default function Credits() {
  const activeKeyRef = useRef("balance");

  const goToPackages = () => {
    activeKeyRef.current = "packages";
    // 通过 Tabs key 切换（由 state 控制）
  };

  return (
    <div>
      <Title level={4}>积分管理</Title>
      <Tabs
        defaultActiveKey="balance"
        items={[
          {
            key: "balance",
            label: "余额概览",
            children: <Balance onGoPackages={goToPackages} />,
          },
          {
            key: "packages",
            label: "充值套餐",
            children: <Packages />,
          },
          {
            key: "history",
            label: "积分流水",
            children: <History />,
          },
        ]}
      />
    </div>
  );
}
```

- [ ] **Step 5: 验证前端编译**

Run: `cd web/frontend && npx tsc --noEmit`

Expected: 无错误

- [ ] **Step 6: 启动开发服务器并手动验证**

Run: `cd web && uv run uvicorn aigc_web.main:app --reload --port 8000` （后端）

Run: `cd web/frontend && npm run dev` （前端）

验证：
- 登录后点击"积分"菜单
- 看到 3 个 Tab（余额概览、充值套餐、积分流水）
- 余额概览显示积分 0
- 套餐页显示空（无上架套餐）
- 流水页显示空表格

- [ ] **Step 7: Commit**

```bash
git add web/frontend/src/pages/
git commit -m "feat(web): implement credits page with Balance, Packages, History tabs"
```

---

## Task 13: 全量回归测试 + 清理

**Files:** 无新增

- [ ] **Step 1: 运行全部后端测试**

Run: `cd web && uv run pytest tests/ -v --tb=short`

Expected: 全部 PASS

- [ ] **Step 2: 运行前端编译检查**

Run: `cd web/frontend && npx tsc --noEmit`

Expected: 无错误

- [ ] **Step 3: 运行前端 lint**

Run: `cd web/frontend && npm run lint`

Expected: 无错误

- [ ] **Step 4: 检查 git status 确认所有改动已提交**

Run: `git status`

Expected: working tree clean（或仅有 `.claude/settings.local.json` 变更）

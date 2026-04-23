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
        total_recharge_cents = db.query(sa_func.coalesce(sa_func.sum(PaymentOrder.amount_cents), 0)).filter(
            PaymentOrder.user_id == user.id, PaymentOrder.status == "paid"
        ).scalar()
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
            "total_recharge_cents": total_recharge_cents,
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
            trade_no=credit_service._generate_trade_no("consume"),
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
    if credits_per_token is not None:
        settings_obj.CREDITS_PER_TOKEN = credits_per_token
    if new_user_bonus_credits is not None:
        settings_obj.NEW_USER_BONUS_CREDITS = new_user_bonus_credits


# --- 流水管理 ---

def list_transactions(
    db: Session,
    user_id: int | None = None,
    type_filter: str | None = None,
    search: str | None = None,
    page: int = 1,
    size: int = 20,
) -> dict:
    """管理后台流水查询，支持按用户、类型、手机号搜索。"""
    query = db.query(CreditTransaction)

    if user_id is not None:
        query = query.filter(CreditTransaction.user_id == user_id)
    if type_filter:
        query = query.filter(CreditTransaction.type == type_filter)
    if search:
        query = query.join(User, User.id == CreditTransaction.user_id).filter(
            User.phone.contains(search)
        )

    total = query.count()
    rows = (
        query.order_by(CreditTransaction.id.desc())
        .offset((page - 1) * size)
        .limit(size)
        .all()
    )

    items = []
    for tx in rows:
        user = db.query(User).filter_by(id=tx.user_id).first()
        items.append({
            "id": tx.id,
            "trade_no": tx.trade_no,
            "user_id": tx.user_id,
            "user_phone": user.phone if user else "",
            "user_nickname": user.nickname if user else "",
            "type": tx.type,
            "amount": tx.amount,
            "balance_after": tx.balance_after,
            "ref_type": tx.ref_type,
            "ref_id": tx.ref_id,
            "remark": tx.remark,
            "created_at": tx.created_at,
        })
    return {"items": items, "total": total, "page": page, "size": size}

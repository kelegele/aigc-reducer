# web/src/aigc_web/services/credit.py
"""积分服务 -- 充值、消费、流水查询、新人赠送。"""

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from aigc_web.config import settings
from aigc_web.models.credit_account import CreditAccount
from aigc_web.models.credit_transaction import CreditTransaction


def _generate_trade_no(tx_type: str) -> str:
    """生成流水号。格式：TX_{type}_{timestamp}_{random}"""
    ts = datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')
    return f"TX_{tx_type}_{ts}_{uuid.uuid4().hex[:8]}"


def recharge(
    db: Session,
    user_id: int,
    amount: int,
    ref_type: str | None = None,
    ref_id: str | int | None = None,
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
        trade_no=_generate_trade_no("recharge"),
    )
    db.add(tx)
    db.commit()


def consume(
    db: Session,
    user_id: int,
    token_count: int,
    ref_type: str | None = None,
    ref_id: str | int | None = None,
    remark: str | None = None,
) -> int:
    """消费积分。按 token_count / 1000 * CREDITS_PER_TOKEN 扣减。返回消耗积分数。"""
    cost = max(1, int(token_count / 1000 * settings.CREDITS_PER_TOKEN))
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
        trade_no=_generate_trade_no("consume"),
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
        query.order_by(CreditTransaction.created_at.desc(), CreditTransaction.id.desc())
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

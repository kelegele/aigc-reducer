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
from aigc_web.schemas.order import OrderDetail, OrderListResponse
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


@router.get("/orders", response_model=OrderListResponse)
def list_orders(
    status: str | None = None,
    page: int = 1,
    size: int = 10,
    user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
):
    return payment_service.list_user_orders(db, user.id, status=status, page=page, size=size)


@router.get("/orders/{order_id}/detail", response_model=OrderDetail)
def get_order_detail(
    order_id: int,
    user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
):
    try:
        return payment_service.get_order_detail(db, order_id, user_id=user.id)
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

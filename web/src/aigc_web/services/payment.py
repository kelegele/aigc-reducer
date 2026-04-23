# web/src/aigc_web/services/payment.py
"""支付服务 — 支付抽象层 + 支付宝实现 + 订单管理。"""

import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from aigc_web.config import settings
from sqlalchemy import func as sa_func

from aigc_web.models.credit_transaction import CreditTransaction
from aigc_web.models.payment_order import PaymentOrder
from aigc_web.models.recharge_package import RechargePackage
from aigc_web.models.user import User
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

    @abstractmethod
    def query_trade(self, out_trade_no: str) -> dict | None:
        """查询交易状态。返回 {"status": "paid", "trade_no": ..., "paid_amount": ...} 或 None。"""


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
                debug=settings.alipay_debug,
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
                timeout_express=f"{settings.ORDER_TIMEOUT_MINUTES}m",
            )
        else:
            order_string = alipay.api_alipay_trade_page_pay(
                out_trade_no=out_trade_no,
                total_amount=str(amount_yuan),
                subject=subject,
                return_url=return_url,
                notify_url=notify_url,
                timeout_express=f"{settings.ORDER_TIMEOUT_MINUTES}m",
            )
        gateway = (
            "https://openapi-sandbox.dl.alipaydev.com/gateway.do?"
            if settings.alipay_debug
            else "https://openapi.alipay.com/gateway.do?"
        )
        return gateway + order_string

    def verify_callback(self, params: dict) -> bool:
        alipay = self._get_alipay()
        return alipay.verify(params, params.get("sign"))

    def query_trade(self, out_trade_no: str) -> dict | None:
        alipay = self._get_alipay()
        resp = alipay.api_alipay_trade_query(out_trade_no=out_trade_no)
        trade_status = resp.get("trade_status")
        if trade_status in ("TRADE_SUCCESS", "TRADE_FINISHED"):
            return {
                "status": "paid",
                "trade_no": resp.get("trade_no"),
                "paid_amount": resp.get("total_amount"),
            }
        return None


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
        return f"/mock-pay?order={out_trade_no}&amount={amount}&return={return_url}"

    def verify_callback(self, params: dict) -> bool:
        return params.get("mock_sign") == "ok"

    def query_trade(self, out_trade_no: str) -> dict | None:
        return None


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
        return_url=settings.get_return_url(order.id),
        notify_url=settings.get_notify_url(),
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
    """查询订单状态。pending 订单会主动查询支付渠道核实支付结果。"""
    order = db.query(PaymentOrder).filter_by(id=order_id, user_id=user_id).first()
    if order is None:
        raise ValueError("订单不存在")

    # pending 订单主动查询支付渠道
    if order.status == "pending":
        provider = get_payment_provider()
        result = provider.query_trade(order.out_trade_no)
        if result:
            handle_payment_callback(db, order.id)
            db.refresh(order)

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


def list_user_orders(
    db: Session,
    user_id: int,
    status: str | None = None,
    page: int = 1,
    size: int = 10,
) -> dict:
    """用户订单列表（分页、状态筛选）。"""
    query = db.query(PaymentOrder).filter_by(user_id=user_id)
    if status:
        query = query.filter(PaymentOrder.status == status)

    total = query.count()
    orders = query.order_by(PaymentOrder.id.desc()).offset((page - 1) * size).limit(size).all()

    items = [
        {
            "id": o.id,
            "out_trade_no": o.out_trade_no,
            "amount_cents": o.amount_cents,
            "credits_granted": o.credits_granted,
            "status": o.status,
            "pay_method": o.pay_method,
            "created_at": o.created_at,
            "paid_at": o.paid_at,
        }
        for o in orders
    ]
    return {"items": items, "total": total, "page": page, "size": size}


def get_order_detail(db: Session, order_id: int, user_id: int | None = None) -> dict:
    """订单详情。user_id=None 时超管用（不校验归属），否则校验归属当前用户。"""
    query = db.query(PaymentOrder)
    if user_id is not None:
        query = query.filter_by(id=order_id, user_id=user_id)
    else:
        query = query.filter_by(id=order_id)

    order = query.first()
    if order is None:
        raise ValueError("订单不存在")

    # 查关联积分流水（对账）
    credit_transaction_id = None
    if order.status == "paid":
        tx = db.query(CreditTransaction).filter_by(
            ref_type="payment_order", ref_id=order.id
        ).first()
        if tx:
            credit_transaction_id = tx.id

    result = {
        "id": order.id,
        "out_trade_no": order.out_trade_no,
        "amount_cents": order.amount_cents,
        "credits_granted": order.credits_granted,
        "status": order.status,
        "pay_method": order.pay_method,
        "created_at": order.created_at,
        "paid_at": order.paid_at,
        "credit_transaction_id": credit_transaction_id,
        "package_name": order.package.name if order.package else "",
    }

    # 超管模式：附加用户信息
    if user_id is None:
        user = db.query(User).filter_by(id=order.user_id).first()
        result["user_id"] = order.user_id
        result["user_phone"] = user.phone if user else ""
        result["user_nickname"] = user.nickname if user else ""

    return result


def list_all_orders(
    db: Session,
    search: str | None = None,
    status: str | None = None,
    page: int = 1,
    size: int = 20,
) -> dict:
    """超管订单列表，支持按订单号/用户手机号搜索。"""
    query = db.query(PaymentOrder)

    if status:
        query = query.filter(PaymentOrder.status == status)

    if search:
        query = query.join(User, User.id == PaymentOrder.user_id).filter(
            (PaymentOrder.out_trade_no.contains(search))
            | (User.phone.contains(search))
        )

    total = query.count()
    orders = query.order_by(PaymentOrder.id.desc()).offset((page - 1) * size).limit(size).all()

    items = []
    for o in orders:
        tx = None
        if o.status == "paid":
            tx = db.query(CreditTransaction).filter_by(
                ref_type="payment_order", ref_id=o.id
            ).first()

        user = db.query(User).filter_by(id=o.user_id).first()
        items.append({
            "id": o.id,
            "out_trade_no": o.out_trade_no,
            "amount_cents": o.amount_cents,
            "credits_granted": o.credits_granted,
            "status": o.status,
            "pay_method": o.pay_method,
            "created_at": o.created_at,
            "paid_at": o.paid_at,
            "credit_transaction_id": tx.id if tx else None,
            "package_name": o.package.name if o.package else "",
            "user_id": o.user_id,
            "user_phone": user.phone if user else "",
            "user_nickname": user.nickname if user else "",
        })

    return {"items": items, "total": total, "page": page, "size": size}


def close_expired_orders(db: Session) -> int:
    """关闭超时的 pending 订单。返回关闭数量。"""
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=settings.ORDER_TIMEOUT_MINUTES)
    expired = (
        db.query(PaymentOrder)
        .filter(
            PaymentOrder.status == "pending",
            PaymentOrder.created_at < cutoff,
        )
        .all()
    )
    for order in expired:
        order.status = "closed"
    db.commit()
    return len(expired)

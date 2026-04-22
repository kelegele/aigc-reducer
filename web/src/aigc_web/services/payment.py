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

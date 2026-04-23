# web/src/aigc_web/services/auth.py
"""认证业务逻辑 — 登录（自动注册）、Token 刷新、用户查询。"""

from sqlalchemy.orm import Session

from aigc_web.config import settings
from aigc_web.models.credit_account import CreditAccount
from aigc_web.models.user import User, generate_user_id
from aigc_web.schemas.auth import LoginResponse, UserResponse
from aigc_web.services import credit as credit_service
from aigc_web.services.token import create_access_token, create_refresh_token, decode_token


def _sync_admin_flag(db: Session, user: User, phone: str) -> None:
    """根据 ADMIN_PHONE 环境变量同步用户超管标识。"""
    should_be_admin = phone == settings.ADMIN_PHONE if settings.ADMIN_PHONE else False
    if user.is_admin != should_be_admin:
        user.is_admin = should_be_admin
        db.commit()
        db.refresh(user)


def login_or_register(db: Session, phone: str) -> LoginResponse:
    """手机号验证码登录。用户不存在则自动创建。"""
    user = db.query(User).filter(User.phone == phone).first()
    if user is None:
        user = User(
            id=generate_user_id(),
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

    # 获取积分余额
    account = db.query(CreditAccount).filter(CreditAccount.user_id == user.id).first()
    balance = account.balance if account else 0

    # ADMIN_PHONE 自动提升超管
    _sync_admin_flag(db, user, phone)

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
            is_admin=user.is_admin,
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
        is_admin=user.is_admin,
        credit_balance=account.balance if account else 0,
    )

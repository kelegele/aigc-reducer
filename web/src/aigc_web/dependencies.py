# web/src/aigc_web/dependencies.py
"""FastAPI 路由公共依赖。"""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from aigc_web.database import get_db
from aigc_web.models.user import User
from aigc_web.schemas.auth import UserResponse
from aigc_web.services.auth import get_current_user, get_user_response
from aigc_web.services.sms import VerificationCodeService

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

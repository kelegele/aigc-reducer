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

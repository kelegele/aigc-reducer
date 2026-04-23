# web/src/aigc_web/routers/auth.py
"""认证相关 API 路由。"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from aigc_web.database import get_db
from aigc_web.dependencies import get_verification_service, require_current_user, require_current_user_response
from aigc_web.schemas.auth import (
    LoginResponse,
    MessageResponse,
    PhoneLoginRequest,
    RefreshRequest,
    SendSmsRequest,
    TokenResponse,
    UpdateProfileRequest,
    UserResponse,
)
from aigc_web.services import auth as auth_service
from aigc_web.services.sms import VerificationCodeService

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/sms/send", response_model=MessageResponse)
def send_sms(
    req: SendSmsRequest,
    sms: VerificationCodeService = Depends(get_verification_service),
):
    try:
        sms.send(req.phone)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    return MessageResponse(message="验证码已发送")


@router.post("/login/phone", response_model=LoginResponse)
def login_by_phone(req: PhoneLoginRequest, db: Session = Depends(get_db)):
    sms: VerificationCodeService = get_verification_service()
    if not sms.verify(req.phone, req.code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="验证码错误或已过期",
        )
    return auth_service.login_or_register(db, req.phone)


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(req: RefreshRequest, db: Session = Depends(get_db)):
    try:
        new_access = auth_service.refresh_access_token(db, req.refresh_token)
        return TokenResponse(
            access_token=new_access,
            refresh_token=req.refresh_token,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e)
        ) from e


@router.get("/me", response_model=UserResponse)
async def get_me(user: UserResponse = Depends(require_current_user_response)):
    return user


@router.put("/me/profile", response_model=UserResponse)
def update_profile(
    req: UpdateProfileRequest,
    user=Depends(require_current_user),
    db: Session = Depends(get_db),
):
    if req.nickname is not None:
        user.nickname = req.nickname
    if req.avatar_url is not None:
        user.avatar_url = req.avatar_url
    db.commit()
    db.refresh(user)
    return auth_service.get_user_response(db, user)

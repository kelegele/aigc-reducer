# web/src/aigc_web/routers/admin.py
"""管理后台 API 路由。"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from aigc_web.config import settings
from aigc_web.database import get_db
from aigc_web.dependencies import require_admin
from aigc_web.models.user import User
from aigc_web.schemas.admin import (
    AdjustCreditsRequest,
    AdminPackageResponse,
    ConfigResponse,
    ConfigUpdateRequest,
    DashboardResponse,
    PackageCreateRequest,
    PackageUpdateRequest,
    SetUserStatusRequest,
    UserListResponse,
)
from aigc_web.schemas.auth import MessageResponse
from aigc_web.schemas.order import AdminOrderDetail, AdminOrderListResponse
from aigc_web.services import admin as admin_service
from aigc_web.services import payment as payment_service

router = APIRouter(prefix="/api/admin", tags=["admin"])


# --- 看板 ---

@router.get("/dashboard", response_model=DashboardResponse)
def get_dashboard(
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return admin_service.get_dashboard(db)


# --- 套餐管理 ---

@router.get("/packages", response_model=list[AdminPackageResponse])
def list_packages(
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return admin_service.list_packages(db)


@router.post("/packages", response_model=AdminPackageResponse)
def create_package(
    req: PackageCreateRequest,
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return admin_service.create_package(db, req)


@router.put("/packages/{package_id}", response_model=AdminPackageResponse)
def update_package(
    package_id: int,
    req: PackageUpdateRequest,
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    try:
        return admin_service.update_package(db, package_id, req)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.delete("/packages/{package_id}", response_model=MessageResponse)
def delete_package(
    package_id: int,
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    try:
        admin_service.delete_package(db, package_id)
        return MessageResponse(message="删除成功")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


# --- 订单管理 ---


@router.get("/orders", response_model=AdminOrderListResponse)
def list_orders(
    search: str | None = None,
    status: str | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return payment_service.list_all_orders(db, search=search, status=status, page=page, size=size)


@router.get("/orders/{order_id}", response_model=AdminOrderDetail)
def get_order_detail(
    order_id: int,
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    try:
        return payment_service.get_order_detail(db, order_id, user_id=None)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


# --- 用户管理 ---

@router.get("/users", response_model=UserListResponse)
def list_users(
    search: str | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    result = admin_service.list_users(db, search=search, page=page, size=size)
    return UserListResponse(**result)


@router.put("/users/{user_id}/credits", response_model=MessageResponse)
def adjust_credits(
    user_id: int,
    req: AdjustCreditsRequest,
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    try:
        admin_service.adjust_credits(db, user_id, req.amount, req.remark)
        return MessageResponse(message="积分调整成功")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.put("/users/{user_id}/status", response_model=MessageResponse)
def set_user_status(
    user_id: int,
    req: SetUserStatusRequest,
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    try:
        admin_service.set_user_status(db, user_id, req.is_active)
        return MessageResponse(message="状态更新成功")
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


# --- 配置 ---

@router.get("/config", response_model=ConfigResponse)
def get_config(
    _admin: User = Depends(require_admin),
):
    return admin_service.get_config()


@router.put("/config", response_model=ConfigResponse)
def update_config(
    req: ConfigUpdateRequest,
    _admin: User = Depends(require_admin),
):
    admin_service.update_config(
        settings,
        credits_per_token=req.credits_per_token,
        new_user_bonus_credits=req.new_user_bonus_credits,
    )
    return admin_service.get_config()

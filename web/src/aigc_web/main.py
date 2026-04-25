# web/src/aigc_web/main.py
"""FastAPI 应用入口。"""

import logging
from contextlib import asynccontextmanager

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from aigc_web.config import settings
from aigc_web.database import SessionLocal
from aigc_web.routers import admin as admin_router
from aigc_web.routers import auth as auth_router
from aigc_web.routers import credits as credits_router
from aigc_web.routers import reduce as reduce_router
from aigc_web.services import payment as payment_service

logger = logging.getLogger(__name__)


def _close_expired_orders_job() -> None:
    """定时任务：关闭超时 pending 订单。"""
    db = SessionLocal()
    try:
        closed = payment_service.close_expired_orders(db)
        if closed > 0:
            logger.info("closed %d expired orders", closed)
    finally:
        db.close()


def _load_config_on_startup() -> None:
    """启动时从 DB 加载系统配置到内存 settings。"""
    from aigc_web.services import admin as admin_service
    db = SessionLocal()
    try:
        admin_service.load_config_from_db(db, settings)
        logger.info("System config loaded from DB")
    except Exception:
        logger.warning("Failed to load config from DB, using defaults", exc_info=True)
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动：加载 DB 配置 + 注册定时任务
    _load_config_on_startup()
    scheduler = BackgroundScheduler()
    scheduler.add_job(_close_expired_orders_job, "interval", seconds=60)
    scheduler.start()
    logger.info("APScheduler started: close_expired_orders every 60s")
    yield
    # 关闭
    scheduler.shutdown(wait=False)


app = FastAPI(title="AIGC Reducer", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router)
app.include_router(credits_router.router)
app.include_router(admin_router.router)
app.include_router(reduce_router.reduce_router)


@app.get("/api/health")
def health_check():
    return {"status": "ok"}

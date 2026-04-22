# web/src/aigc_web/main.py
"""FastAPI 应用入口。"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from aigc_web.config import settings
from aigc_web.routers import admin as admin_router
from aigc_web.routers import auth as auth_router
from aigc_web.routers import credits as credits_router

app = FastAPI(title="AIGC Reducer", version="0.1.0")

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


@app.get("/api/health")
def health_check():
    return {"status": "ok"}

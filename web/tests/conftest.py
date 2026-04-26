# web/tests/conftest.py
"""测试配置 — 使用 SQLite 内存数据库。"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from aigc_web.database import Base, get_db
from aigc_web.config import settings


@pytest.fixture(autouse=True)
def _disable_dev_bypass(monkeypatch):
    """确保测试环境不跳过验证码校验，且配置使用默认值。"""
    monkeypatch.setattr(settings, "DEV_BYPASS_PHONE", False)
    monkeypatch.setattr(settings, "DEV_TEST_PHONES", "")
    monkeypatch.setattr(settings, "SITE_URL", "http://localhost:5173")
    monkeypatch.setattr(settings, "CREDITS_PER_1K_TOKENS", 1.0)
    monkeypatch.setattr(settings, "NEW_USER_BONUS_CREDITS", 0)


@pytest.fixture
def db_engine():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session(db_engine):
    Session = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    session = Session()
    yield session
    session.close()

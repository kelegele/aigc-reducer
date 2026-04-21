# web/tests/conftest.py
"""测试配置 — 使用 SQLite 内存数据库。"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from aigc_web.database import Base, get_db


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

# web/tests/test_dependencies.py
"""依赖注入测试。"""

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from aigc_web.database import Base, get_db
from aigc_web.dependencies import require_current_user
from aigc_web.models.user import User
from aigc_web.services.token import create_access_token

app = FastAPI()


@app.get("/test-me")
async def _test_me(user: User = Depends(require_current_user)):
    return {"phone": user.phone}


def test_require_current_user_valid_token(db_engine):
    Session = sessionmaker(bind=db_engine)
    session = Session()
    user = User(phone="13800138000", nickname="测试")
    session.add(user)
    session.commit()

    token = create_access_token(user.id)
    app.dependency_overrides[get_db] = lambda: session
    client = TestClient(app)
    resp = client.get("/test-me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["phone"] == "13800138000"
    app.dependency_overrides.clear()
    session.close()


def test_require_current_user_no_token():
    app.dependency_overrides.pop(get_db, None)
    client = TestClient(app)
    resp = client.get("/test-me")
    assert resp.status_code == 401

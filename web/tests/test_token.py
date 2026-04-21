# web/tests/test_token.py
"""JWT token 创建和验证测试。"""

import pytest

from aigc_web.services.token import create_access_token, create_refresh_token, decode_token


def test_create_and_decode_access_token():
    token = create_access_token(user_id=42)
    user_id = decode_token(token, expected_type="access")
    assert user_id == 42


def test_create_and_decode_refresh_token():
    token = create_refresh_token(user_id=42)
    user_id = decode_token(token, expected_type="refresh")
    assert user_id == 42


def test_decode_access_token_with_wrong_type():
    token = create_access_token(user_id=42)
    with pytest.raises(ValueError, match="token 类型错误"):
        decode_token(token, expected_type="refresh")


def test_decode_invalid_token():
    with pytest.raises(ValueError, match="无效的 token"):
        decode_token("invalid.token.here", expected_type="access")


def test_different_users_get_different_tokens():
    token1 = create_access_token(user_id=1)
    token2 = create_access_token(user_id=2)
    assert token1 != token2
    assert decode_token(token1, "access") == 1
    assert decode_token(token2, "access") == 2

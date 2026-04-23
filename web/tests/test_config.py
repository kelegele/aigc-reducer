# web/tests/test_config.py
"""配置计算属性测试。"""

from aigc_web.config import Settings


def test_alipay_debug_localhost():
    s = Settings(SITE_URL="http://localhost:5173")
    assert s.alipay_debug is True


def test_alipay_debug_production():
    s = Settings(SITE_URL="https://aigc-reducer.com")
    assert s.alipay_debug is False


def test_get_return_url():
    s = Settings(SITE_URL="http://localhost:5173")
    assert s.get_return_url(42) == "http://localhost:5173/credits?order_id=42"


def test_get_notify_url():
    s = Settings(SITE_URL="http://localhost:5173")
    assert s.get_notify_url() == "http://localhost:5173/api/credits/payment/callback"


def test_get_return_url_production():
    s = Settings(SITE_URL="https://aigc-reducer.com")
    assert s.get_return_url(99) == "https://aigc-reducer.com/credits?order_id=99"

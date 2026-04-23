# 支付宝真实接入 — 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 从 Mock 支付切换到真实支付宝沙箱，用主动查询（alipay.trade.query）替代回调作为支付确认主路径。

**Architecture:** 在 PaymentProvider 抽象层新增 `query_trade()` 方法，后端收到订单查询请求时若订单仍为 pending 则主动调支付宝核实。环境配置用 `SITE_URL` 单一变量替代三个手动 URL，自动推断沙箱/正式。

**Tech Stack:** Python + FastAPI + python-alipay-sdk + React + TypeScript + Ant Design

---

### Task 1: config.py — 新增 SITE_URL + computed properties

**Files:**
- Modify: `web/src/aigc_web/config.py`
- Create: `web/tests/test_config.py`

- [ ] **Step 1: 写测试 — 验证 SITE_URL 计算属性**

创建 `web/tests/test_config.py`：

```python
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
```

- [ ] **Step 2: 运行测试，确认失败**

Run: `cd web && uv run pytest tests/test_config.py -v`
Expected: FAIL — `alipay_debug`, `get_return_url`, `get_notify_url` 不存在

- [ ] **Step 3: 实现 config.py 改造**

在 `web/src/aigc_web/config.py` 的 `Settings` 类中：

1. 新增 `SITE_URL` 字段（在 `CORS_ORIGINS` 之后）：
```python
SITE_URL: str = "http://localhost:5173"
```

2. 在 `Settings` 类末尾、`model_config` 之前，新增三个方法：
```python
@property
def alipay_debug(self) -> bool:
    """自动推断：localhost = 沙箱，否则 = 正式。"""
    return "localhost" in self.SITE_URL

def get_return_url(self, order_id: int) -> str:
    """支付宝同步跳转地址（用户浏览器回跳到前端）。"""
    return f"{self.SITE_URL}/credits?order_id={order_id}"

def get_notify_url(self) -> str:
    """支付宝异步回调地址（支付宝服务器调用后端）。"""
    return f"{self.SITE_URL}/api/credits/payment/callback"
```

3. 保留旧的 `ALIPAY_RETURN_URL`、`ALIPAY_NOTIFY_URL`、`ALIPAY_DEBUG` 字段不变（后续 Task 4 清理）。

- [ ] **Step 4: 运行测试，确认通过**

Run: `cd web && uv run pytest tests/test_config.py -v`
Expected: 5 PASS

- [ ] **Step 5: 运行全量测试，确认无回归**

Run: `cd web && uv run pytest tests/ -v`
Expected: 全部 PASS（旧字段仍保留，不应有回归）

- [ ] **Step 6: Commit**

```bash
git add web/src/aigc_web/config.py web/tests/test_config.py
git commit -m "feat(web): add SITE_URL with computed alipay_debug, return_url, notify_url"
```

---

### Task 2: payment.py — PaymentProvider 新增 query_trade

**Files:**
- Modify: `web/src/aigc_web/services/payment.py`

- [ ] **Step 1: 写测试 — AlipayProvider.query_trade 和 MockPaymentProvider.query_trade**

在 `web/tests/test_payment_service.py` 末尾追加：

```python
def test_mock_provider_query_trade_returns_none():
    from aigc_web.services.payment import MockPaymentProvider
    provider = MockPaymentProvider()
    assert provider.query_trade("any_order") is None


@patch("aigc_web.services.payment.settings")
def test_alipay_provider_query_trade_paid(mock_settings):
    mock_settings.ALIPAY_APP_ID = "test-id"
    mock_settings.ALIPAY_PRIVATE_KEY = "key"
    mock_settings.ALIPAY_PUBLIC_KEY = "pub"
    mock_settings.ALIPAY_DEBUG = True

    from aigc_web.services.payment import AlipayProvider
    provider = AlipayProvider()
    provider._alipay = MagicMock()
    provider._alipay.api_alipay_trade_query.return_value = {
        "trade_status": "TRADE_SUCCESS",
        "trade_no": "ALIPAY_TRADE_123",
        "total_amount": "10.00",
    }

    result = provider.query_trade("PAY_TEST_001")
    assert result is not None
    assert result["status"] == "paid"
    assert result["trade_no"] == "ALIPAY_TRADE_123"


@patch("aigc_web.services.payment.settings")
def test_alipay_provider_query_trade_not_paid(mock_settings):
    mock_settings.ALIPAY_APP_ID = "test-id"
    mock_settings.ALIPAY_PRIVATE_KEY = "key"
    mock_settings.ALIPAY_PUBLIC_KEY = "pub"
    mock_settings.ALIPAY_DEBUG = True

    from aigc_web.services.payment import AlipayProvider
    provider = AlipayProvider()
    provider._alipay = MagicMock()
    provider._alipay.api_alipay_trade_query.return_value = {
        "trade_status": "WAIT_BUYER_PAY",
    }

    result = provider.query_trade("PAY_TEST_002")
    assert result is None


@patch("aigc_web.services.payment.settings")
def test_alipay_provider_query_trade_finished(mock_settings):
    """TRADE_FINISHED 也视为已支付。"""
    mock_settings.ALIPAY_APP_ID = "test-id"
    mock_settings.ALIPAY_PRIVATE_KEY = "key"
    mock_settings.ALIPAY_PUBLIC_KEY = "pub"
    mock_settings.ALIPAY_DEBUG = True

    from aigc_web.services.payment import AlipayProvider
    provider = AlipayProvider()
    provider._alipay = MagicMock()
    provider._alipay.api_alipay_trade_query.return_value = {
        "trade_status": "TRADE_FINISHED",
        "trade_no": "ALIPAY_TRADE_456",
        "total_amount": "20.00",
    }

    result = provider.query_trade("PAY_TEST_003")
    assert result is not None
    assert result["status"] == "paid"
```

- [ ] **Step 2: 运行测试，确认失败**

Run: `cd web && uv run pytest tests/test_payment_service.py::test_mock_provider_query_trade_returns_none tests/test_payment_service.py::test_alipay_provider_query_trade_paid tests/test_payment_service.py::test_alipay_provider_query_trade_not_paid tests/test_payment_service.py::test_alipay_provider_query_trade_finished -v`
Expected: FAIL — `query_trade` 方法不存在

- [ ] **Step 3: 实现 query_trade**

在 `web/src/aigc_web/services/payment.py` 中：

1. 在 `PaymentProvider` 抽象基类中新增抽象方法（在 `verify_callback` 之后）：

```python
@abstractmethod
def query_trade(self, out_trade_no: str) -> dict | None:
    """查询交易状态。返回 {"status": "paid", "trade_no": ..., "paid_amount": ...} 或 None。"""
```

2. 在 `AlipayProvider` 中实现（在 `verify_callback` 之后）：

```python
def query_trade(self, out_trade_no: str) -> dict | None:
    alipay = self._get_alipay()
    resp = alipay.api_alipay_trade_query(out_trade_no=out_trade_no)
    trade_status = resp.get("trade_status")
    if trade_status in ("TRADE_SUCCESS", "TRADE_FINISHED"):
        return {
            "status": "paid",
            "trade_no": resp.get("trade_no"),
            "paid_amount": resp.get("total_amount"),
        }
    return None
```

3. 在 `MockPaymentProvider` 中实现（在 `verify_callback` 之后）：

```python
def query_trade(self, out_trade_no: str) -> dict | None:
    return None
```

- [ ] **Step 4: 运行测试，确认通过**

Run: `cd web && uv run pytest tests/test_payment_service.py::test_mock_provider_query_trade_returns_none tests/test_payment_service.py::test_alipay_provider_query_trade_paid tests/test_payment_service.py::test_alipay_provider_query_trade_not_paid tests/test_payment_service.py::test_alipay_provider_query_trade_finished -v`
Expected: 4 PASS

- [ ] **Step 5: Commit**

```bash
git add web/src/aigc_web/services/payment.py web/tests/test_payment_service.py
git commit -m "feat(web): add query_trade to PaymentProvider for active payment verification"
```

---

### Task 3: payment.py — query_order_status 增加主动查询

**Files:**
- Modify: `web/src/aigc_web/services/payment.py`
- Modify: `web/tests/test_payment_service.py`

- [ ] **Step 1: 写测试 — pending 订单主动查询后变 paid**

在 `web/tests/test_payment_service.py` 末尾追加：

```python
@patch("aigc_web.services.payment.get_payment_provider")
def test_query_order_status_active_query_confirms_payment(mock_get_provider, db_session):
    """pending 订单查询时，后端主动调 query_trade，发现已支付则更新。"""
    user, pkg = _setup_user_and_package(db_session)
    order = PaymentOrder(
        user_id=user.id,
        package_id=pkg.id,
        out_trade_no="PAY_ACTIVE_001",
        amount_cents=1000,
        credits_granted=110,
        status="pending",
        pay_method="pc_web",
    )
    db_session.add(order)
    db_session.commit()

    mock_provider = MagicMock()
    mock_provider.query_trade.return_value = {
        "status": "paid",
        "trade_no": "ALIPAY_123",
        "paid_amount": "10.00",
    }
    mock_get_provider.return_value = mock_provider

    result = payment_service.query_order_status(db_session, order.id, user.id)
    assert result["status"] == "paid"
    assert result["paid_at"] is not None

    # 积分到账
    account = db_session.query(CreditAccount).filter_by(user_id=user.id).one()
    assert account.balance == 110

    # 幂等：再查一次不重复加积分
    result2 = payment_service.query_order_status(db_session, order.id, user.id)
    assert result2["status"] == "paid"
    assert db_session.query(CreditAccount).filter_by(user_id=user.id).one().balance == 110


@patch("aigc_web.services.payment.get_payment_provider")
def test_query_order_status_active_query_still_pending(mock_get_provider, db_session):
    """query_trade 返回 None（未支付），订单保持 pending。"""
    user, pkg = _setup_user_and_package(db_session)
    order = PaymentOrder(
        user_id=user.id,
        package_id=pkg.id,
        out_trade_no="PAY_ACTIVE_002",
        amount_cents=1000,
        credits_granted=110,
        status="pending",
        pay_method="pc_web",
    )
    db_session.add(order)
    db_session.commit()

    mock_provider = MagicMock()
    mock_provider.query_trade.return_value = None
    mock_get_provider.return_value = mock_provider

    result = payment_service.query_order_status(db_session, order.id, user.id)
    assert result["status"] == "pending"
```

- [ ] **Step 2: 运行测试，确认失败**

Run: `cd web && uv run pytest tests/test_payment_service.py::test_query_order_status_active_query_confirms_payment tests/test_payment_service.py::test_query_order_status_active_query_still_pending -v`
Expected: FAIL — 当前 `query_order_status` 不会主动查询

- [ ] **Step 3: 实现 query_order_status 主动查询逻辑**

修改 `web/src/aigc_web/services/payment.py` 中的 `query_order_status` 函数（约 204-219 行），替换为：

```python
def query_order_status(db: Session, order_id: int, user_id: int) -> dict:
    """查询订单状态。pending 订单会主动查询支付宝核实支付结果。"""
    order = db.query(PaymentOrder).filter_by(id=order_id, user_id=user_id).first()
    if order is None:
        raise ValueError("订单不存在")

    # pending 订单主动查询支付渠道
    if order.status == "pending":
        provider = get_payment_provider()
        result = provider.query_trade(order.out_trade_no)
        if result:
            handle_payment_callback(db, order.id)
            db.refresh(order)

    return {
        "id": order.id,
        "out_trade_no": order.out_trade_no,
        "amount_cents": order.amount_cents,
        "credits_granted": order.credits_granted,
        "status": order.status,
        "pay_method": order.pay_method,
        "created_at": order.created_at,
        "paid_at": order.paid_at,
    }
```

- [ ] **Step 4: 运行测试，确认通过**

Run: `cd web && uv run pytest tests/test_payment_service.py::test_query_order_status_active_query_confirms_payment tests/test_payment_service.py::test_query_order_status_active_query_still_pending -v`
Expected: 2 PASS

- [ ] **Step 5: 运行全量测试**

Run: `cd web && uv run pytest tests/ -v`
Expected: 全部 PASS（旧的 `test_query_order_status` 仍通过，因为它没 mock get_payment_provider 所以 query_trade 会走默认的 MockPaymentProvider 返回 None，订单保持 pending）

- [ ] **Step 6: Commit**

```bash
git add web/src/aigc_web/services/payment.py web/tests/test_payment_service.py
git commit -m "feat(web): query_order_status actively verifies payment via trade query"
```

---

### Task 4: payment.py — 切换到动态 URL + 清理旧配置

**Files:**
- Modify: `web/src/aigc_web/config.py`
- Modify: `web/src/aigc_web/services/payment.py`
- Modify: `web/.env.example`
- Modify: `web/tests/conftest.py`

- [ ] **Step 1: 修改 payment.py — create_recharge_order 使用动态 URL**

在 `web/src/aigc_web/services/payment.py` 的 `create_recharge_order` 函数中，将：

```python
return_url=settings.ALIPAY_RETURN_URL,
notify_url=settings.ALIPAY_NOTIFY_URL,
```

替换为：

```python
return_url=settings.get_return_url(order.id),
notify_url=settings.get_notify_url(),
```

- [ ] **Step 2: 修改 payment.py — AlipayProvider 使用 alipay_debug property**

在 `web/src/aigc_web/services/payment.py` 的 `AlipayProvider.create_order` 方法中，将所有 `settings.ALIPAY_DEBUG` 替换为 `settings.alipay_debug`：

```python
gateway = (
    "https://openapi-sandbox.go.alipaydev.com/gateway.do?"
    if settings.alipay_debug
    else "https://openapi.alipay.com/gateway.do?"
)
```

- [ ] **Step 3: 从 config.py 删除旧字段**

在 `web/src/aigc_web/config.py` 中，删除这三个字段：

```python
ALIPAY_NOTIFY_URL: str = ""
ALIPAY_RETURN_URL: str = ""
ALIPAY_DEBUG: bool = True
```

确保 `SITE_URL` 字段和三个 computed 方法保留。

- [ ] **Step 4: 更新 .env.example**

用以下内容替换 `.env.example` 中的支付宝相关部分：

```env
# 站点地址（决定沙箱/正式环境 + 回调 URL）
# localhost = 自动使用支付宝沙箱
# 正式域名 = 自动使用正式环境
SITE_URL=http://localhost:5173

# 支付宝
ALIPAY_APP_ID=
ALIPAY_PRIVATE_KEY=
ALIPAY_PUBLIC_KEY=
```

删除旧的 `ALIPAY_DEBUG`、`ALIPAY_NOTIFY_URL`、`ALIPAY_RETURN_URL` 注释行。

- [ ] **Step 5: 更新 conftest.py — patch SITE_URL**

在 `web/tests/conftest.py` 的 `_disable_dev_bypass` fixture 中追加一行，确保测试环境有 SITE_URL：

```python
@pytest.fixture(autouse=True)
def _disable_dev_bypass(monkeypatch):
    """确保测试环境不跳过验证码校验。"""
    monkeypatch.setattr(settings, "DEV_BYPASS_PHONE", False)
    monkeypatch.setattr(settings, "DEV_TEST_PHONES", "")
    monkeypatch.setattr(settings, "SITE_URL", "http://localhost:5173")
```

- [ ] **Step 6: 运行全量测试**

Run: `cd web && uv run pytest tests/ -v`
Expected: 全部 PASS

- [ ] **Step 7: Commit**

```bash
git add web/src/aigc_web/config.py web/src/aigc_web/services/payment.py web/.env.example web/tests/conftest.py
git commit -m "refactor(web): replace ALIPAY_*_URL/DEBUG with SITE_URL computed properties"
```

---

### Task 5: 前端 — Packages.tsx 回跳检测 + 状态 UI

**Files:**
- Modify: `web/frontend/src/pages/credits/Packages.tsx`

- [ ] **Step 1: 修改 Packages.tsx**

完整替换 `web/frontend/src/pages/credits/Packages.tsx`：

```tsx
// web/frontend/src/pages/credits/Packages.tsx
import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import {
  App as AntApp,
  Card,
  Row,
  Col,
  Button,
  Typography,
  Tag,
  Alert,
  Spin,
} from "antd";
import { InfoCircleOutlined } from "@ant-design/icons";
import { useCreditsStore } from "../../stores/credits";
import { createRecharge, getOrder } from "../../api/credits";

const { Title, Text } = Typography;

const packageScenes: Record<string, string> = {
  "体验包": "适合体验用户",
  "基础包": "适合本科论文",
  "标准包": "适合硕博论文",
  "专业包": "适合多篇论文",
  "豪华包": "适合团队使用",
};

export default function Packages() {
  const { packages, fetchPackages, fetchBalance } = useCreditsStore();
  const { message, modal } = AntApp.useApp();
  const [payingOrderId, setPayingOrderId] = useState<number | null>(null);
  const [polling, setPolling] = useState(false);
  const [confirming, setConfirming] = useState(false);

  useEffect(() => {
    fetchPackages();
  }, [fetchPackages]);

  useEffect(() => {
    // 检测支付宝回跳（return_url 带 order_id 参数）
    const params = new URLSearchParams(window.location.search);
    const orderId = params.get("order_id");
    if (orderId) {
      // 清掉 URL 参数，避免刷新重复触发
      window.history.replaceState({}, "", "/credits");
      const id = parseInt(orderId, 10);
      if (!isNaN(id)) {
        setPayingOrderId(id);
        setConfirming(true);
        startPolling(id);
      }
    }
  }, []);

  const handleRecharge = async (pkgId: number, pkgName: string, price: number) => {
    modal.confirm({
      title: "确认充值",
      content: `套餐：${pkgName}，金额：¥${(price / 100).toFixed(2)}`,
      onOk: async () => {
        try {
          const result = await createRecharge({
            package_id: pkgId,
            pay_method: "pc_web",
          });
          setPayingOrderId(result.order_id);
          window.location.href = result.pay_url;
        } catch (err: unknown) {
          const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
          message.error(detail || "创建订单失败");
        }
      },
    });
  };

  const startPolling = (orderId: number) => {
    setPolling(true);
    let count = 0;
    const interval = setInterval(async () => {
      count++;
      if (count > 30) {
        clearInterval(interval);
        setPolling(false);
        setConfirming(false);
        message.warning("支付结果未确认，请稍后在订单列表中查看");
        return;
      }
      try {
        const order = await getOrder(orderId);
        if (order.status === "paid") {
          clearInterval(interval);
          setPolling(false);
          setConfirming(false);
          setPayingOrderId(null);
          message.success("充值成功！");
          fetchBalance();
        }
      } catch {
        // 继续轮询
      }
    }, 2000);
  };

  return (
    <div>
      <Title level={5}>选择充值套餐</Title>

      {/* 支付结果确认中 */}
      {confirming && (
        <Alert
          type="info"
          showIcon
          icon={<Spin size="small" />}
          message="支付结果确认中..."
          description="正在查询支付结果，请稍候"
          style={{ marginBottom: 16 }}
        />
      )}

      {/* 积分用途说明 */}
      <Alert
        type="info"
        showIcon
        icon={<InfoCircleOutlined />}
        message="积分用途说明"
        description="积分用于文档检测和 AI 改写。系统按实际消耗的 Token 数量扣减积分（每 1000 Token 消耗一定积分，具体价格请参见套餐详情）。"
        style={{ marginBottom: 16 }}
      />

      <Row gutter={[16, 16]}>
        {packages.map((pkg) => {
          const pricePerCredit = pkg.price_cents / (pkg.credits + pkg.bonus_credits);
          const scene = packageScenes[pkg.name] || "通用套餐";

          return (
            <Col xs={24} sm={12} md={8} key={pkg.id}>
              <Card hoverable>
                <div style={{ textAlign: "center" }}>
                  <Title level={4} style={{ marginBottom: 4 }}>
                    {pkg.name}
                  </Title>
                  <Tag color="blue" style={{ marginBottom: 12 }}>
                    {scene}
                  </Tag>
                  <div style={{ margin: "16px 0" }}>
                    <Text style={{ fontSize: 32, fontWeight: "bold" }}>
                      ¥{(pkg.price_cents / 100).toFixed(0)}
                    </Text>
                  </div>
                  <div style={{ marginBottom: 8 }}>
                    <Text>{pkg.credits} 积分</Text>
                    {pkg.bonus_credits > 0 && (
                      <Tag color="red" style={{ marginLeft: 8 }}>
                        赠送 {pkg.bonus_credits}
                      </Tag>
                    )}
                  </div>
                  <div style={{ marginBottom: 12 }}>
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      约 ¥{(pricePerCredit / 100).toFixed(3)}/积分
                    </Text>
                  </div>
                </div>
                <Button
                  type="primary"
                  block
                  loading={polling && payingOrderId !== null}
                  onClick={() =>
                    handleRecharge(pkg.id, pkg.name, pkg.price_cents)
                  }
                >
                  立即充值
                </Button>
              </Card>
            </Col>
          );
        })}
      </Row>
      {packages.length === 0 && (
        <Card>
          <Text type="secondary">暂无可用套餐</Text>
        </Card>
      )}
    </div>
  );
}
```

改动要点：
- 新增 `confirming` state 控制确认中提示
- 新增 `useEffect` 检测 URL `order_id` 参数，触发自动轮询
- `startPolling` 不再在 `handleRecharge` 里调用（跳转到支付宝后不再轮询当前页面）
- `startPolling` 超时时 `setConfirming(false)` 并提示用户
- 导入 `useSearchParams` 改为不使用（直接用 `window.location.search`）
- 新增 `Spin` 导入用于确认中图标

- [ ] **Step 2: 手动验证前端**

Run: `cd web/frontend && npm run build`
Expected: 构建成功，无 TypeScript 错误

- [ ] **Step 3: Commit**

```bash
git add web/frontend/src/pages/credits/Packages.tsx
git commit -m "feat(web): detect Alipay return URL, auto-poll with status indicator"
```

---

### Task 6: 最终验证

- [ ] **Step 1: 运行全量后端测试**

Run: `cd web && uv run pytest tests/ -v`
Expected: 全部 PASS

- [ ] **Step 2: 运行前端构建**

Run: `cd web/frontend && npm run build`
Expected: 构建成功

- [ ] **Step 3: 最终提交（如有遗漏的文件）**

```bash
git add -A
git status  # 确认没有遗漏或意外文件
git commit -m "chore: final cleanup for Alipay live integration"
```

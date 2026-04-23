# 支付宝真实接入：主动查询方案 + 环境配置改造

## Context

支付宝电脑网站支付产品已签约，需要从 Mock/骨架阶段切换到真实支付宝沙箱接入。当前支付确认完全依赖异步回调（notify_url），但本地开发无公网地址，回调无法到达。生产环境回调也可能丢失。

核心改动：引入主动查询（alipay.trade.query）作为支付确认的主路径，回调降级为补充。同时用 `SITE_URL` 统一环境配置。

## 设计决策

| 决策 | 选择 | 理由 |
|------|------|------|
| 支付确认主路径 | 前端轮询 + 后端主动查询 | 本地无需公网穿透，生产环境也更可靠 |
| 环境区分 | `SITE_URL` 单一变量自动推断 | 删掉 3 个手动配置，减少出错 |
| 开发策略 | 先沙箱后正式 | 沙箱可反复测试不涉及真实资金 |
| 回调保留 | 是 | 生产环境作为补充，不删除 |

## 支付流程

```
用户点击充值
    |
后端创建订单，返回 Alipay 支付链接（return_url 含 order_id）
    |
浏览器跳转到支付宝付款页
    |
用户完成支付
    |
支付宝跳回 return_url（/credits?order_id=123）
    |
前端检测 URL 参数，自动启动轮询
    |
后端发现订单是 pending -> 调 alipay.trade.query 查支付宝
    |
查到已支付 -> 更新订单 + 积分到账 -> 返回 paid
    |
前端展示成功
```

## 后端改动

### 1. config.py 改造

新增 `SITE_URL`，删除 `ALIPAY_RETURN_URL`、`ALIPAY_NOTIFY_URL`、`ALIPAY_DEBUG`：

```python
class Settings(BaseSettings):
    # 站点地址（环境区分的唯一入口）
    SITE_URL: str = "http://localhost:5173"

    # 支付宝配置（保留）
    ALIPAY_APP_ID: str = ""
    ALIPAY_PRIVATE_KEY: str = ""
    ALIPAY_PUBLIC_KEY: str = ""

    # --- 以下改为 computed properties ---

    @property
    def alipay_debug(self) -> bool:
        """自动推断：localhost = 沙箱，否则 = 正式"""
        return "localhost" in self.SITE_URL

    def get_return_url(self, order_id: int) -> str:
        """支付宝同步跳转地址（用户浏览器回跳到前端）"""
        return f"{self.SITE_URL}/credits?order_id={order_id}"

    def get_notify_url(self) -> str:
        """支付宝异步回调地址（支付宝服务器调用后端）"""
        return f"{self.SITE_URL}/api/credits/payment/callback"
```

注意：`notify_url` 在本地开发时支付宝无法访问，但代码保留该参数。生产环境部署后自动生效。

### 2. PaymentProvider 增加 query_trade

抽象基类新增方法：

```python
class PaymentProvider(ABC):
    @abstractmethod
    def create_order(self, ...) -> str: ...

    @abstractmethod
    def verify_callback(self, params: dict) -> bool: ...

    @abstractmethod
    def query_trade(self, out_trade_no: str) -> dict | None:
        """主动查询支付宝交易状态。返回 None 表示未支付/未找到。"""
```

AlipayProvider 实现：

```python
class AlipayProvider(PaymentProvider):
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

MockPaymentProvider 实现：

```python
class MockPaymentProvider(PaymentProvider):
    def query_trade(self, out_trade_no: str) -> dict | None:
        return None  # Mock 模式靠 callback 更新，不支持主动查询
```

### 3. query_order_status 改造

在现有 `query_order_status()` 中增加主动查询逻辑：

```python
def query_order_status(db: Session, order_id: int, user_id: int) -> dict:
    order = db.query(PaymentOrder).filter_by(id=order_id, user_id=user_id).first()
    if order is None:
        raise ValueError("订单不存在")

    # pending 订单主动查询支付宝
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

### 4. create_order 中 return_url 动态拼接

```python
def create_recharge_order(db, user_id, package_id, pay_method):
    ...
    order = PaymentOrder(...)
    db.add(order)
    db.commit()
    db.refresh(order)

    provider = get_payment_provider()
    pay_url = provider.create_order(
        ...
        return_url=settings.get_return_url(order.id),  # 动态拼接
        notify_url=settings.get_notify_url(),           # 动态拼接
    )
    return {"order_id": order.id, "pay_url": pay_url}
```

### 5. AlipayProvider 引用 settings.alipay_debug

现有 `create_order()` 中 `settings.ALIPAY_DEBUG` 改为 `settings.alipay_debug`（computed property）。

## 前端改动

### 1. Packages.tsx — 回跳检测 + 自动轮询

检测 URL 中的 `order_id` 参数，自动启动轮询并显示状态提示：

```tsx
const [confirming, setConfirming] = useState(false);

useEffect(() => {
  const params = new URLSearchParams(window.location.search);
  const orderId = params.get("order_id");
  if (orderId) {
    // 清掉 URL 参数，避免刷新重复触发
    window.history.replaceState({}, "", "/credits");
    const id = parseInt(orderId, 10);
    setPayingOrderId(id);
    setConfirming(true);
    startPolling(id);
  }
}, []);
```

### 2. 支付确认中状态 UI

```tsx
{confirming && (
  <Alert
    type="info"
    showIcon
    message="支付结果确认中..."
    description="正在查询支付结果，请稍候"
    style={{ marginBottom: 16 }}
  />
)}
```

轮询成功后 `setConfirming(false)` 并显示成功提示；超时后提示"支付结果未确认，请稍后查看订单"。

### 3. 轮询成功回调

```tsx
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
```

### 4. handleRecharge 中的 return_url

不再需要前端处理 `return_url`，因为后端 `create_order` 已经动态拼接了包含 `order_id` 的 `return_url`。支付宝跳回时 URL 自带 `order_id` 参数。

但注意：支付宝跳回时会附加额外参数（`out_trade_no`、`sign` 等），与我们的 `order_id` 参数并存。前端只需读取 `order_id` 即可。

## 支付宝沙箱接入步骤

### 1. 获取沙箱密钥

1. 登录支付宝开放平台 -> 控制台 -> 沙箱
2. 沙箱自动分配 `APPID`（如 `9021000...`）
3. 用支付宝密钥生成工具生成 RSA2 密钥对
4. 上传应用公钥到沙箱应用 -> 获得支付宝公钥
5. 保留应用私钥

### 2. 配置 .env

```env
# 站点地址（自动决定沙箱/正式环境）
SITE_URL=http://localhost:5173

# 支付宝沙箱凭据
ALIPAY_APP_ID=9021000xxxxxxxx
ALIPAY_PRIVATE_KEY=MIIEvgIBADANBg...（应用私钥）
ALIPAY_PUBLIC_KEY=MIIBIjANBgkqhk...（支付宝公钥）
```

### 3. 测试流程

1. 启动后端 + 前端
2. 登录 -> 充值页面 -> 选套餐 -> 点击充值
3. 浏览器跳转支付宝沙箱收银台
4. 用沙箱买家账号完成支付
5. 跳回前端 `/credits?order_id=123` -> 自动轮询 -> 后端主动查询确认 -> 积分到账

### 4. 切换正式环境

```env
SITE_URL=https://你的域名
ALIPAY_APP_ID=正式APPID
ALIPAY_PRIVATE_KEY=正式应用私钥
ALIPAY_PUBLIC_KEY=正式支付宝公钥
```

`alipay_debug` 自动变为 `False`，网关自动切换到正式环境。

## 文件变更清单

| 操作 | 文件 | 说明 |
|------|------|------|
| Modify | `web/src/aigc_web/config.py` | 删 3 个变量，加 `SITE_URL` + computed properties |
| Modify | `web/src/aigc_web/services/payment.py` | 加 `query_trade`，改造 `query_order_status` 和 `create_recharge_order` |
| Modify | `web/frontend/src/pages/credits/Packages.tsx` | 回跳检测 + 自动轮询 + 状态提示 |
| Modify | `web/.env.example` | 更新配置说明，用 `SITE_URL` 替代旧变量 |

## 不在范围内

- 微信支付
- 退款/冲正
- 支付宝证书模式（当前用公钥模式）
- 前端订单确认页（当前直接跳转支付宝）

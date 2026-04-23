# P2 补全：Pending 订单超时自动关闭

## Context

支付对接已完成（AlipayProvider + MockProvider + 订单管理）。当前 pending 订单无过期机制，用户创建订单后永不关闭，占用订单号段且影响对账。需要 15 分钟后自动关闭未支付的 pending 订单。

## 方案：支付平台 timeout + 本地定时扫描

### 1. AlipayProvider：timeout_express

`create_order()` 中所有 API 调用新增 `timeout_express="15m"` 参数。支付宝收银台自动显示倒计时，到期后支付宝关闭交易，用户无法继续支付。

### 2. 本地定时任务：APScheduler

应用启动时注册 APScheduler BackgroundScheduler，每 60 秒扫描 `status="pending" AND created_at < now() - ORDER_TIMEOUT_MINUTES` 的订单，批量改为 `closed`。

超时阈值通过 `config.py` 的 `ORDER_TIMEOUT_MINUTES` 配置，默认 15。

### 3. 关闭前查询（仅 AlipayProvider 有 APP_ID 时）

对配置了 `ALIPAY_APP_ID` 的环境，关闭前调 `alipay_trade_query` 确认支付状态，防止用户已付款但回调丢失导致误关。查询结果为 `TRADE_SUCCESS` 或 `TRADE_FINISHED` 则跳过关闭并触发到账逻辑。

MockProvider 环境不做查询，直接关闭。

### 4. 配置

`config.py` 新增：

```python
ORDER_TIMEOUT_MINUTES: int = 15  # pending 订单超时时间（分钟）
```

## 文件变更

| 操作 | 路径 | 说明 |
|------|------|------|
| Modify | `web/src/aigc_web/config.py` | 新增 `ORDER_TIMEOUT_MINUTES=15` |
| Modify | `web/src/aigc_web/services/payment.py` | AlipayProvider 加 timeout_express；新增 `close_expired_orders()` |
| Modify | `web/src/aigc_web/main.py` | 启动时注册 APScheduler |
| Add dep | `web/pyproject.toml` | 新增 `apscheduler` 依赖 |
| Create | `web/tests/test_order_timeout.py` | 超时关闭测试 |

## 不在范围内

- 已关闭订单的退款（closed 订单从未付款，无需退款）
- 主动查询对账（P3 范围）
- 订单状态变更通知（推送/WebSocket）

# 支付对接 + 订单管理 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 完成支付宝对接（沙箱+生产）、订单管理（用户+超管）、Mock支付页面、支付宝商户审核所需的三个页面截图。

**Architecture:** 在现有 PaymentProvider 抽象层上修复 AlipayProvider 沙箱 URL、改进 MockProvider；新增订单列表/详情 API（用户侧+超管侧）；前端增加"我的订单"tab、超管订单管理页、Mock 支付页、Dashboard 产品介绍区。

**Tech Stack:** FastAPI + SQLAlchemy 2.0 + Alembic (backend), React 19 + TypeScript + Ant Design (frontend)

---

## Task 1: 修复 AlipayProvider 沙箱 URL

**Files:**
- Modify: `web/src/aigc_web/services/payment.py:83`

- [ ] 修改 `AlipayProvider.create_order()` 的 return 语句，根据 `settings.ALIPAY_DEBUG` 选择网关地址

```python
gateway = (
    "https://openapi-sandbox.go.alipaydev.com/gateway.do?"
    if settings.ALIPAY_DEBUG
    else "https://openapi.alipay.com/gateway.do?"
)
return gateway + order_string
```

- [ ] 修改 `MockPaymentProvider.create_order()` 返回内部 mock 页面 URL

```python
return f"/mock-pay?order={out_trade_no}&amount={amount}&return={return_url}"
```

- [ ] 修改 `MockPaymentProvider.verify_callback()` 增加验签参数

```python
def verify_callback(self, params: dict) -> bool:
    return params.get("mock_sign") == "ok"
```

- [ ] 运行测试确认通过

## Task 2: 后端订单 Schema + 服务层

**Files:**
- Create: `web/src/aigc_web/schemas/order.py`
- Modify: `web/src/aigc_web/services/payment.py`
- Modify: `web/src/aigc_web/services/admin.py`

- [ ] 创建 `schemas/order.py`：OrderListItem、OrderDetail（含 credit_transaction_id + package_name）、AdminOrderDetail、OrderListResponse

```python
class OrderListItem(BaseModel):
    id: int
    out_trade_no: str
    amount_cents: int
    credits_granted: int
    status: str
    pay_method: str
    created_at: datetime
    paid_at: datetime | None

class OrderDetail(OrderListItem):
    credit_transaction_id: int | None
    package_name: str

class AdminOrderDetail(OrderDetail):
    user_id: int
    user_phone: str
    user_nickname: str

class OrderListResponse(BaseModel):
    items: list[OrderListItem]
    total: int
    page: int
    size: int
```

- [ ] 在 `services/payment.py` 新增 `list_user_orders(db, user_id, status, page, size)` 和 `get_order_detail(db, order_id, user_id=None)`

`get_order_detail` 中：若 status=paid，通过 `CreditTransaction` 查 `ref_type="payment_order", ref_id=order.id` 获取 `credit_transaction_id`。通过 `order.package` 关联获取 `package_name`。

- [ ] 在 `services/admin.py` 新增 `list_all_orders(db, search, status, page, size)`

支持按订单号/用户手机号搜索，按状态筛选。返回 `AdminOrderDetail` 列表。

## Task 3: 后端订单路由

**Files:**
- Modify: `web/src/aigc_web/routers/credits.py`
- Modify: `web/src/aigc_web/routers/admin.py`

- [ ] 在 `credits.py` 新增：
  - `GET /api/credits/orders` — 用户订单列表（分页、状态筛选）
  - `GET /api/credits/orders/{id}/detail` — 订单详情（含关联流水信息）

- [ ] 在 `admin.py` 新增：
  - `GET /api/admin/orders` — 全部订单列表（分页、搜索、状态筛选）
  - `GET /api/admin/orders/{id}` — 订单详情（含关联流水、用户信息）

- [ ] 修改回调路由 `payment_callback`：MockProvider 验签时检查 `mock_sign=ok` 参数

## Task 4: 后端测试

**Files:**
- Create: `web/tests/test_order_service.py`
- Create: `web/tests/test_order_router.py`

- [ ] `test_order_service.py`：测试 list_user_orders、get_order_detail（含对账验证）、list_all_orders
- [ ] `test_order_router.py`：测试用户订单列表、订单详情、超管订单列表接口

## Task 5: 前端订单 API + 用户订单页

**Files:**
- Create: `web/frontend/src/api/orders.ts`
- Create: `web/frontend/src/pages/credits/Orders.tsx`
- Modify: `web/frontend/src/pages/Credits.tsx`

- [ ] 创建 `api/orders.ts`：getOrders、getOrderDetail、getAdminOrders、getAdminOrderDetail

- [ ] 创建 `pages/credits/Orders.tsx`：订单列表（Table），展示订单号、金额（元）、积分、状态 Tag、时间。点击展开详情显示流水 ID。

- [ ] 修改 `Credits.tsx`：在 tabs 中增加"我的订单"tab（在"充值套餐"和"积分流水"之间）

## Task 6: 超管订单管理页

**Files:**
- Create: `web/frontend/src/pages/admin/AdminOrders.tsx`
- Modify: `web/frontend/src/components/AppLayout.tsx`
- Modify: `web/frontend/src/App.tsx`

- [ ] 创建 `AdminOrders.tsx`：订单列表 Table，列含订单号、用户手机号、金额（元）、积分、状态 Tag、创建时间。支持状态筛选 Select + 搜索 Input。

- [ ] 修改 `AppLayout.tsx`：管理子菜单增加"订单管理"项（在"套餐管理"之后）

- [ ] 修改 `App.tsx`：注册 `/admin/orders` 路由

## Task 7: Mock 支付页面

**Files:**
- Create: `web/frontend/src/pages/MockPay.tsx`
- Modify: `web/frontend/src/App.tsx`

- [ ] 创建 `MockPay.tsx`：读取 URL 参数（order, amount, return），展示订单号和金额，"模拟支付成功"按钮调用 `/api/credits/payment/callback?mock_sign=ok&out_trade_no=xxx`，成功后跳转 return URL。

- [ ] 修改 `App.tsx`：注册 `/mock-pay` 路由（无需登录保护）

## Task 8: Dashboard 产品介绍区（支付宝首页截图）

**Files:**
- Modify: `web/frontend/src/pages/Dashboard.tsx`

- [ ] 在现有统计卡片下方增加产品介绍区块：
  - "什么是 AIGC Reducer" 简介段落
  - 核心功能卡片（检测引擎、改写风格、输出报告）
  - 操作流程（上传 → 扫描 → 改写 → 下载）

## Task 9: Packages 增强（支付宝商品页截图）

**Files:**
- Modify: `web/frontend/src/pages/credits/Packages.tsx`

- [ ] 页面顶部增加"积分用途说明"：检测和改写按 token 消耗积分
- [ ] 套餐卡片增加"适用场景"标签（如"适合本科论文"）
- [ ] 显示单价信息

## Task 10: 提交 + 更新文档

- [ ] 更新 CLAUDE.md API endpoints 表
- [ ] 提交所有变更

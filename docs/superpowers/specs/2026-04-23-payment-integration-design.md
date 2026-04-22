# P2 补全：支付对接 + 订单管理

## Context

P2 搭了积分充值的骨架（PaymentProvider 抽象层 + AlipayProvider + MockProvider），但支付对接还没真正调通：收银台跳转、回调验签、沙箱环境适配都有问题。订单管理也缺失：用户看不到自己的充值订单，超管无法全局查看订单。

P2.5 的超管后台已经完成套餐管理、用户管理、数据看板，但缺订单管理模块。

## 支付宝接入配置指南

### 1. 开通支付宝开发者账号

1. 登录 [支付宝开放平台](https://open.alipay.com/)，用企业支付宝账号登录（个人账号只能用沙箱）
2. 进入「控制台」→「创建应用」→ 选择「网页/移动应用」
3. 填写应用名称（如"AIGC Reducer"），提交审核（沙箱环境无需审核）

### 2. 获取关键参数

| 参数 | 在哪获取 | 说明 |
|------|---------|------|
| `ALIPAY_APP_ID` | 控制台 → 应用详情 → AppID | 应用唯一标识 |
| `ALIPAY_PRIVATE_KEY` | 自己生成，见下方 | 应用私钥，用于签名请求 |
| `ALIPAY_PUBLIC_KEY` | 上传公钥后平台给出 | 支付宝公钥，用于验签回调 |
| `ALIPAY_NOTIFY_URL` | 自己的服务器地址 | 支付宝异步通知地址，必须 HTTPS |
| `ALIPAY_RETURN_URL` | 自己的前端地址 | 支付完成后跳转的前端页面 |

### 3. 生成 RSA2 密钥对

```bash
# 安装 openssl（Windows 用 Git Bash 或安装 OpenSSL）
# 生成私钥
openssl genrsa -out app_private_key.pem 2048

# 从私钥提取公钥
openssl rsa -in app_private_key.pem -pubout -out app_public_key.pem
```

然后在支付宝开放平台 → 应用详情 → 「开发设置」→「接口加签方式」→ 上传 `app_public_key.pem` 的内容，平台会给你「支付宝公钥」（注意不是你生成的那个公钥，是平台返回的）。

### 4. 配置 .env 文件

```bash
# web/.env

# 支付宝 —— 沙箱环境（开发测试用）
ALIPAY_APP_ID=9021000xxxxxxxxx          # 沙箱 AppID
ALIPAY_PRIVATE_KEY=MIIEvgIBADANBg...    # 你的应用私钥（整个 PEM 内容，一行）
ALIPAY_PUBLIC_KEY=MIIBIjANBgkqhk...     # 支付宝公钥（平台给的，不是你自己生成的）
ALIPAY_DEBUG=true                        # true = 沙箱环境
ALIPAY_NOTIFY_URL=https://your-ngrok-url.ngrok.io/api/credits/payment/callback
ALIPAY_RETURN_URL=http://localhost:5176/credits  # 支付完跳回前端

# 支付宝 —— 生产环境
# ALIPAY_APP_ID=2021000xxxxxxxxx        # 正式 AppID
# ALIPAY_PRIVATE_KEY=...
# ALIPAY_PUBLIC_KEY=...
# ALIPAY_DEBUG=false
# ALIPAY_NOTIFY_URL=https://yourdomain.com/api/credits/payment/callback
# ALIPAY_RETURN_URL=https://yourdomain.com/credits
```

### 5. 沙箱环境

支付宝提供完整的沙箱测试环境：
- 沙箱 AppID 和密钥在 [开放平台沙箱](https://open.alipay.com/develop/sandbox/app) 获取
- 沙箱买家账号和登录密码也在沙箱页面提供
- 沙箱网关地址：`https://openapi-sandbox.go.alipaydev.com/gateway.do?`（代码中 `ALIPAY_DEBUG=true` 时自动使用）
- 沙箱支付不需要真实扣款

### 6. 开发环境回调方案

支付宝异步通知（notify_url）需要公网可访问。开发环境用内网穿透：

```bash
# 方案 A：ngrok（推荐）
ngrok http 9898
# 会得到类似 https://xxxx.ngrok.io 的地址
# 设 ALIPAY_NOTIFY_URL=https://xxxx.ngrok.io/api/credits/payment/callback

# 方案 B：cpolar（国内替代）
cpolar http 9898
```

### 7. 应用上线前检查

- [ ] 应用审核通过（开放平台提交审核）
- [ ] 签约「手机网站支付」和「电脑网站支付」产品
- [ ] 域名备案完成，notify_url 必须是备案域名 + HTTPS
- [ ] 密钥从沙箱切换为生产密钥
- [ ] `ALIPAY_DEBUG=false`

## 核心原则：订单与流水严格对账

订单和积分流水必须能互相追溯，确保资金链路清晰：

| 保证 | 实现方式 |
|------|---------|
| 每笔 paid 订单有且仅有一条充值流水 | `handle_payment_callback` 写流水时用 `ref_type="payment_order"`, `ref_id=order.id` |
| 流水金额 = 订单积分数 | `CreditTransaction.amount` = `PaymentOrder.credits_granted`（已有逻辑保证） |
| pending 订单没有流水 | 只有 `status=paid` 才触发 `credit_service.recharge()` |
| 订单详情能查到对应流水 | API 返回关联的 `credit_transaction_id` |
| 超管能交叉核验 | 超管订单列表展示对应流水 ID，流水列表展示对应订单号 |

## 支付对接

### AlipayProvider 修复

当前问题：
1. 收银台 URL 写死了生产地址，沙箱环境应用 `https://openapi-sandbox.go.alipaydev.com/gateway.do?`
2. `ALIPAY_DEBUG=true` 时应自动使用沙箱地址

修复方案：`AlipayProvider.create_order()` 根据 `settings.ALIPAY_DEBUG` 选择网关地址：

```python
def create_order(self, ...):
    alipay = self._get_alipay()
    amount_yuan = amount / 100

    if pay_method == "h5":
        order_string = alipay.api_alipay_trade_wap_pay(...)
    else:
        order_string = alipay.api_alipay_trade_page_pay(...)

    gateway = "https://openapi-sandbox.go.alipaydev.com/gateway.do?" if settings.ALIPAY_DEBUG else "https://openapi.alipay.com/gateway.do?"
    return gateway + order_string
```

### MockProvider 改进

开发环境需要可测试的支付流程：

```python
class MockPaymentProvider(PaymentProvider):
    def create_order(self, out_trade_no, amount, subject, return_url, notify_url, pay_method):
        # 返回一个前端可识别的 mock 页面 URL
        return f"/mock-pay?order={out_trade_no}&amount={amount}&return={return_url}"

    def verify_callback(self, params):
        return params.get("mock_sign") == "ok"
```

新增前端 Mock 支付页面 `/mock-pay`：展示订单信息，点击"模拟支付成功"后调用回调接口并跳转。

### 支付回调流程

```
用户点击充值 → 创建订单(pending) → 跳转支付宝收银台
                                        ↓
                              用户完成支付
                                        ↓
                    支付宝异步通知 → /api/credits/payment/callback
                                        ↓
                          验签 → 更新订单为 paid → 写入积分流水
                                        ↓
                    支付宝同步跳转 → return_url → 前端轮询订单状态
```

开发环境回调方案：
- MockProvider：前端模拟支付后直接调用 callback 接口
- AlipayProvider 沙箱：需要公网可访问的 notify_url（开发用 ngrok 或类似工具）

## 订单管理

### 用户侧

| Method | Path | 说明 |
|--------|------|------|
| GET | `/api/credits/orders` | 用户订单列表（分页、状态筛选） |
| GET | `/api/credits/orders/{id}` | 订单详情（含关联流水信息） |

### 超管侧

| Method | Path | 说明 |
|--------|------|------|
| GET | `/api/admin/orders` | 全部订单列表（分页、搜索、状态筛选） |
| GET | `/api/admin/orders/{id}` | 订单详情（含关联流水、用户信息） |

### 订单 Schema

```python
class OrderListItem(BaseModel):
    id: int
    out_trade_no: str
    amount_cents: int
    credits_granted: int
    status: str               # pending / paid / closed
    pay_method: str            # pc_web / h5
    created_at: datetime
    paid_at: datetime | None

class OrderDetail(OrderListItem):
    # 对账信息：paid 订单关联的积分流水
    credit_transaction_id: int | None   # 对应的积分流水 ID
    package_name: str                    # 套餐名称（冗余展示用）
```

### 超管订单扩展

```python
class AdminOrderDetail(OrderDetail):
    user_id: int
    user_phone: str
    user_nickname: str
```

### 服务层

`services/payment.py` 新增：

- `list_user_orders(db, user_id, status, page, size)` — 用户订单分页
- `get_order_detail(db, order_id, user_id=None)` — 订单详情（user_id=None 时超管用，不校验归属）

`services/admin.py` 新增：

- `list_all_orders(db, search, status, page, size)` — 超管订单列表，支持按用户手机号/订单号搜索

对账查询：`get_order_detail` 中，若订单 status=paid，通过 `ref_type="payment_order", ref_id=order.id` 查询对应的积分流水，返回 `credit_transaction_id`。

## 前端

### 用户订单页

在积分管理 Tabs 中增加"我的订单"tab：

```
积分管理 → 余额概览 | 充值套餐 | 我的订单 | 积分流水
```

订单列表展示：订单号、金额（元）、积分、状态（Tag 颜色区分）、创建时间、支付时间。
点击可展开详情，paid 订单显示对应的积分流水 ID。

### 超管订单页

管理后台新增"订单管理"菜单：

```
管理 → 数据看板 | 套餐管理 | 订单管理 | 用户管理 | 积分配置
```

订单列表：订单号、用户手机号、金额、积分、状态、时间。
支持状态筛选和搜索。

### Mock 支付页面（仅开发环境）

路由 `/mock-pay`：展示订单号和金额，"模拟支付成功"按钮触发回调。

## 文件变更

### 后端

| 操作 | 路径 | 说明 |
|------|------|------|
| Modify | `web/src/aigc_web/services/payment.py` | 修复沙箱 URL、改进 Mock、新增 list/get 订单 |
| Modify | `web/src/aigc_web/routers/credits.py` | 新增用户订单列表和详情接口 |
| Create | `web/src/aigc_web/schemas/order.py` | 订单相关 Schema |
| Modify | `web/src/aigc_web/services/admin.py` | 新增超管订单列表 |
| Modify | `web/src/aigc_web/routers/admin.py` | 新增超管订单路由 |

### 前端

| 操作 | 路径 | 说明 |
|------|------|------|
| Create | `web/frontend/src/api/orders.ts` | 订单 API |
| Modify | `web/frontend/src/pages/Credits.tsx` | 增加"我的订单"tab |
| Create | `web/frontend/src/pages/credits/Orders.tsx` | 用户订单列表 |
| Create | `web/frontend/src/pages/admin/AdminOrders.tsx` | 超管订单管理 |
| Modify | `web/frontend/src/components/AppLayout.tsx` | 管理菜单加订单 |
| Create | `web/frontend/src/pages/MockPay.tsx` | Mock 支付页面 |
| Modify | `web/frontend/src/App.tsx` | 注册新路由 |

### 测试

| 操作 | 路径 | 说明 |
|------|------|------|
| Create | `web/tests/test_order_service.py` | 订单服务测试（对账验证） |
| Create | `web/tests/test_order_router.py` | 订单路由集成测试 |

## 支付宝商户审核页面

签约支付宝商户支付产品需要提交 3 张网站截图：首页、商品/服务页、支付页。这些页面必须开发完整、可截图。

### 1. 首页截图（/dashboard）

当前 Dashboard 仅显示欢迎语和两个统计卡片，内容不足以通过审核。需要增加：

- **产品介绍区**：简明说明产品是什么（"学术论文 AIGC 查重率降低工具"）、解决什么问题
- **核心功能卡片**：检测（规则+LLM 双引擎）、改写（5 种风格）、输出（差异对比+整改建议）
- **操作流程**：上传文档 → 扫描风险 → 选择风格 → AI 改写 → 下载结果

布局方案：在现有统计卡片下方增加产品介绍和功能说明区块。

### 2. 商品/服务页截图（/credits 充值套餐 tab）

当前 Packages 页面已有套餐卡片，基本可用，但需要增强：

- **页面顶部**：增加"积分说明"区块，解释积分用途（检测、改写按 token 扣积分）
- **套餐卡片**：增加"适用场景"说明（如"适合本科论文"、"适合硕博论文"）
- **定价说明**：显示每积分单价，让页面更像正式的商品页

### 3. 支付页截图（收银台/确认支付页）

当前流程是点击"立即充值"后直接跳转支付宝，缺少中间的订单确认页。需要新增：

- **订单确认页 `/checkout`**（Modal 形式也可以）：展示套餐名、金额、积分数、支付方式选择
- **支付中转页**：Mock 支付页面 `/mock-pay`，展示订单信息 + "模拟支付"按钮
- **支付结果页**：支付成功/失败提示

对于支付宝审核，Mock 支付页足以作为"支付页"截图。真实环境中用户会跳转到支付宝收银台。

### 实现优先级

这三个页面对支付宝商户审核是硬性要求，必须在首次提交审核前完成。开发顺序：

1. Dashboard 产品介绍区（首页截图）
2. Packages 增强（商品页截图）
3. Checkout + Mock 支付页（支付页截图）

## 不在范围内

- 退款/冲正
- 订单超时自动关闭
- 支付宝主动查询（轮询对账）
- 微信支付

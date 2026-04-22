# P2: 积分充值与支付系统设计

## Context

Web 服务 P1 已完成用户认证骨架（手机号+短信验证码登录、JWT、React 前端）。P2 目标是建立积分经济闭环：用户充值积分 → 积分用于论文检测/改写（P3）。本文档覆盖支付集成、充值套餐、积分消费引擎、交易流水和前端积分账户页面。

## 决策记录

| 决策项 | 选择 | 理由 |
|--------|------|------|
| 支付渠道 | 支付宝官方 SDK | 有个体工商户，无中间商抽成 |
| 支付方式 | PC 网站支付 + H5 手机支付 | 根据用户端自动选择 |
| 套餐管理 | 数据库存储，可扩展 | 后续 admin 可动态管理 |
| 积分消费 | 按 token 扣积分 | 与检测/改写直接挂钩 |
| token 汇率 | 可配置项（`CREDITS_PER_TOKEN`） | 方便后续调价 |
| 交易流水 | 标准版：充值+消费都记 | 含余额快照、关联订单/任务 ID |
| 支付回调 | 验签 + 幂等 + 到账，无实时推送 | 标准处理，前端轮询订单状态 |
| 新人赠送 | 可配置（`NEW_USER_BONUS_CREDITS`） | 注册时自动发放 |
| 前端范围 | 完整积分账户（余额 + 套餐 + 流水） | 三个 Tab 页 |

## 数据库模型

### 新增表

**RechargePackage（充值套餐）**

| 字段 | 类型 | 说明 |
|------|------|------|
| id | int PK autoincrement | |
| name | str(50) | 套餐名（如"基础包"、"专业包"） |
| price_cents | int | 价格（分），避免浮点精度问题 |
| credits | int | 到账积分数 |
| bonus_credits | int, default 0 | 赠送积分 |
| sort_order | int, default 0 | 展示排序（升序） |
| is_active | bool, default True | 是否上架 |
| created_at | datetime | |

**PaymentOrder（支付订单）**

| 字段 | 类型 | 说明 |
|------|------|------|
| id | int PK autoincrement | |
| user_id | int FK → users.id | |
| package_id | int FK → recharge_packages.id | |
| out_trade_no | str(64) unique | 商户订单号（自动生成） |
| amount_cents | int | 实付金额（分） |
| credits_granted | int | 应到账积分（含赠送） |
| status | enum(pending/paid/failed/closed) | 订单状态 |
| pay_method | str(20) | pc_web / h5 |
| paid_at | datetime nullable | 支付成功时间 |
| created_at | datetime | |
| updated_at | datetime | |

**CreditTransaction（积分流水）**

| 字段 | 类型 | 说明 |
|------|------|------|
| id | int PK autoincrement | |
| user_id | int FK → users.id | |
| type | enum(recharge/consume) | 流水类型 |
| amount | int | 积分变动（正数充值，负数消费） |
| balance_after | int | 操作后余额快照 |
| ref_type | str(30) nullable | 关联类型：payment_order / detection_task |
| ref_id | int nullable | 关联 ID |
| remark | str(200) nullable | 备注（如"充值-专业包"、"检测扣费-2000 token"） |
| created_at | datetime | |

### 现有表变更

无结构变更。`CreditAccount` 已有的 `balance`、`total_recharged`、`total_consumed` 字段够用。

### 新增配置项（config.py）

```python
# 积分配置
NEW_USER_BONUS_CREDITS: int = 0          # 新人赠送积分
CREDITS_PER_TOKEN: float = 1.0           # 每 token 消耗积分数

# 支付宝配置
ALIPAY_APP_ID: str = ""
ALIPAY_PRIVATE_KEY: str = ""             # 应用私钥
ALIPAY_PUBLIC_KEY: str = ""              # 支付宝公钥
ALIPAY_NOTIFY_URL: str = ""              # 异步回调地址
ALIPAY_RETURN_URL: str = ""              # 同步跳转地址
ALIPAY_DEBUG: bool = True                # 沙箱模式开关
```

## 后端架构

### 支付抽象层

```
PaymentProvider (抽象类)
├── create_order(out_trade_no, amount, subject, return_url, notify_url, pay_method) → pay_url
├── verify_callback(params) → bool
└── query_order(out_trade_no) → OrderStatus

AlipayProvider (PaymentProvider 实现)
├── PC: alipay.trade.page.pay（电脑网站支付）
├── H5: alipay.trade.wap.pay（手机网站支付）
└── 基于 python-alipay-sdk，处理密钥签名/验签
```

`pay_method` 由前端传入：根据 user_agent 或显式参数标记 `pc_web` / `h5`。

### 服务模块

**services/payment.py（支付服务）**

- `create_recharge_order(user_id, package_id, pay_method)` — 校验套餐 → 创建 PaymentOrder → 调用 AlipayProvider 获取支付链接 → 返回 pay_url + order_id
- `handle_payment_callback(params)` — 验签 → 幂等检查（订单已 paid 则直接返回 success） → 更新订单为 paid → 调用 credit.recharge() 加积分 → 记流水
- `query_order_status(order_id, user_id)` — 查询订单状态（供前端轮询），校验订单归属当前用户

**services/credit.py（积分服务）**

- `recharge(user_id, credits, ref_type, ref_id, remark)` — 事务内：加 balance + 加 total_recharged + 写 CreditTransaction
- `consume(user_id, token_count, ref_type, ref_id, remark)` — 按 token_count × CREDITS_PER_TOKEN 计算扣减积分 → 余额不足抛 403 → 事务内：减 balance + 加 total_consumed + 写 CreditTransaction
- `get_transactions(user_id, type_filter, page, size)` — 分页查询流水，支持按 type 筛选，默认时间倒序
- `get_balance(user_id)` — 查余额（复用 CreditAccount 查询）
- `grant_new_user_bonus(user_id)` — 检查配置，若 > 0 则调用 recharge()

### 事务与幂等

- 所有积分变动（recharge/consume）在同一数据库事务内完成：更新 CreditAccount + 写 CreditTransaction
- 支付回调幂等：先 SELECT 订单状态，若已为 paid 则直接返回 success，不重复加积分
- 积分服务的 recharge/consume 方法先查 balance_after 写入流水，确保快照准确

### API 路由

| Method | Path | 认证 | 说明 |
|--------|------|------|------|
| GET | `/api/credits/packages` | JWT | 获取上架充值套餐列表 |
| POST | `/api/credits/recharge` | JWT | 创建充值订单 → 返回 `{ pay_url, order_id }` |
| GET | `/api/credits/orders/{id}` | JWT | 查询订单状态（校验归属） |
| POST | `/api/credits/payment/callback` | 无 | 支付宝异步回调通知 |
| GET | `/api/credits/transactions` | JWT | 积分流水（分页 + 类型筛选） |
| GET | `/api/credits/balance` | JWT | 查询余额 |

请求/响应 Schema（schemas/credits.py）：

```python
# 创建充值订单
class RechargeRequest(BaseModel):
    package_id: int
    pay_method: Literal["pc_web", "h5"]

class RechargeResponse(BaseModel):
    order_id: int
    pay_url: str

# 订单状态
class OrderResponse(BaseModel):
    id: int
    out_trade_no: str
    amount_cents: int
    credits_granted: int
    status: str
    pay_method: str
    created_at: datetime
    paid_at: datetime | None

# 套餐
class PackageResponse(BaseModel):
    id: int
    name: str
    price_cents: int
    credits: int
    bonus_credits: int

# 流水
class TransactionResponse(BaseModel):
    id: int
    type: str          # recharge / consume
    amount: int
    balance_after: int
    remark: str | None
    created_at: datetime

class TransactionListResponse(BaseModel):
    items: list[TransactionResponse]
    total: int
    page: int
    size: int
```

### 注册流程调整

P1 的 `services/auth.py` 注册流程新增一步：

```
创建 User → 创建 CreditAccount → credit.grant_new_user_bonus(user_id)
```

无需额外幂等保护，注册流程本身只执行一次。

## 前端设计

### 路由与页面结构

```
/credits → Credits.tsx（积分账户主页面，Ant Design Tabs）
  ├── Tab 1: Balance.tsx    — 余额概览（默认 Tab）
  ├── Tab 2: Packages.tsx   — 套餐展示 + 充值
  └── Tab 3: History.tsx    — 积分流水
```

### 余额概览（Balance.tsx）

- 大数字展示当前积分余额（Statistic 组件）
- 快捷充值入口（跳转到套餐 Tab）
- 最近 5 条流水摘要列表

### 套餐展示 / 充值（Packages.tsx）

- 卡片式布局展示上架套餐，每张卡片显示：价格、积分数、赠送积分（高亮标注）
- 点击"立即充值" → Modal 确认（套餐详情 + 价格）
- 确认后调用 `POST /api/credits/recharge` → 获取 pay_url
- PC 端 `window.location.href = pay_url` 跳转支付宝收银台
- H5 端同样跳转（支付宝自动唤起 App）
- 支付完成后跳回积分账户页（return_url 指向前端）
- 前端轮询 `GET /api/credits/orders/{id}`（每 2 秒，最多 30 次），paid 后刷新余额

### 积分流水（History.tsx）

- Ant Design Table，分页加载
- 列：时间、类型（Tag 颜色区分：充值绿/消费红）、积分变动（+/-）、余额、备注
- 筛选：全部 / 充值 / 消费
- 默认时间倒序

### 新增前端文件

```
pages/Credits.tsx              — 改造为 Tabs 容器
pages/credits/Balance.tsx      — 余额概览 Tab
pages/credits/Packages.tsx     — 套餐展示 + 充值流程
pages/credits/History.tsx      — 积分流水列表
api/credits.ts                 — 积分相关 API 调用函数
stores/credits.ts              — Zustand store（余额、流水缓存）
```

### 支付跳转流程

```
用户选套餐 → 点击充值 → 确认弹窗
  → POST /api/credits/recharge → { pay_url, order_id }
  → 跳转支付宝（PC 收银台 / H5 唤起 App）
  → 支付完成 → 跳回积分账户页
  → 前端轮询订单状态（2s × 30）
  → paid → 刷新余额 + 成功提示
```

## 不在 P2 范围内

- 微信支付（后续按需接入，PaymentProvider 抽象层预留扩展）
- 退款/冲正
- Admin 后台管理套餐（仅预留数据结构，P4 实现）
- 积分过期/冻结
- 优惠券/折扣码
- 生产环境短信服务商对接（仍沿用 P1 的 dev 模式）

## 依赖

- `python-alipay-sdk` — 支付宝 Python SDK
- 现有依赖（FastAPI、SQLAlchemy、Alembic、Pydantic）无需新增

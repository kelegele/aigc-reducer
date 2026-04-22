# P2.5: 账号角色体系与超管后台设计

## Context

Web 服务 P1 完成用户认证，P2 完成积分充值支付。P2.5 目标：建立账号角色体系（超管/普通用户），超管可通过管理后台配置套餐、积分价格、管理用户和查看数据看板。同时增加开发环境测试账号支持。

## 决策记录

| 决策项 | 选择 | 理由 |
|--------|------|------|
| 超管创建方式 | 手动在 DB 设置 is_admin=True | 超管唯一，不需要注册流程 |
| 超管数量 | 唯一一个 | 业务简单，避免多超管权限管理 |
| 前端形态 | 同一应用，超管导航栏多出"管理"菜单 | 不需要独立前端，减少维护成本 |
| 管理后台路由 | `/api/admin/*` 前缀，统一 `require_admin` 依赖 | 权限控制集中，代码清晰 |
| 开发环境跳过验证 | 环境变量配置 `DEV_TEST_PHONES` + `DEV_BYPASS_PHONE` | 灵活支持开发和测试场景 |
| 积分配置存储 | config.py（环境变量）+ admin API 读写 | 不额外建配置表，简单够用 |

## 角色体系

### 现有基础

User 模型已有 `is_admin` 字段（bool, default=False）。无需新增字段。

### 权限控制

新增依赖注入 `require_admin`：

```python
async def require_admin(user: User = Depends(require_current_user)) -> User:
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return user
```

所有 `/api/admin/*` 路由使用此依赖。

### 超管创建

手动在数据库执行：
```sql
UPDATE users SET is_admin = 1 WHERE phone = '13424369869';
```

## 开发环境测试账号

### 新增配置项（config.py）

```python
DEV_TEST_PHONES: str = ""         # 逗号分隔的测试手机号
DEV_BYPASS_PHONE: bool = False    # True = 所有手机号跳过验证码
```

### SMS 服务改造

在 `services/sms.py` 的 `verify()` 方法中，开发环境下增加跳过逻辑：

```
if settings.SMS_PROVIDER == "dev":
    bypass_phones = [p.strip() for p in settings.DEV_TEST_PHONES.split(",") if p.strip()]
    if settings.DEV_BYPASS_PHONE or phone in bypass_phones:
        return True  # 跳过验证码检查
```

- `DEV_BYPASS_PHONE=true`：所有手机号任意 6 位验证码可登录
- `DEV_TEST_PHONES=134xxx,138xxx`：仅指定手机号跳过验证码
- 两者都不配置：现有行为不变，仍需从控制台查看验证码

## 后端架构

### 新增/修改文件

| 操作 | 路径 | 职责 |
|------|------|------|
| Modify | `web/src/aigc_web/config.py` | 新增 DEV_TEST_PHONES、DEV_BYPASS_PHONE |
| Modify | `web/src/aigc_web/dependencies.py` | 新增 require_admin 依赖 |
| Create | `web/src/aigc_web/schemas/admin.py` | 管理 API Schema |
| Create | `web/src/aigc_web/services/admin.py` | 管理服务（套餐CRUD、用户管理、看板、配置） |
| Create | `web/src/aigc_web/routers/admin.py` | 管理 API 路由 |
| Modify | `web/src/aigc_web/main.py` | 注册 admin 路由 |
| Modify | `web/src/aigc_web/services/sms.py` | 开发环境跳过验证码 |
| Create | `web/tests/test_admin_service.py` | 管理服务单元测试 |
| Create | `web/tests/test_admin_router.py` | 管理 API 集成测试 |

### 服务层（services/admin.py）

**套餐管理：**
- `list_packages(db)` — 所有套餐（含已下架），按 sort_order 排序
- `create_package(db, data)` — 创建套餐
- `update_package(db, package_id, data)` — 修改套餐（名称/价格/积分/赠送/排序/上下架）
- `delete_package(db, package_id)` — 删除套餐（硬删除，仅无关联订单时允许）

**用户管理：**
- `list_users(db, search, page, size)` — 分页查询用户列表，支持手机号/昵称搜索
- `adjust_credits(db, user_id, amount, remark)` — 手动调整积分（正加负减），记流水
- `set_user_status(db, user_id, is_active)` — 禁用/启用账号

**数据看板：**
- `get_dashboard(db)` — 返回：
  - `total_users` — 总用户数
  - `total_revenue_cents` — 总充值收入（分）
  - `total_credits_granted` — 总积分发放
  - `total_credits_consumed` — 总积分消费
  - `today_new_users` — 今日新增用户
  - `top_recharge_users` — 充值 Top 10（用户+金额）
  - `top_consume_users` — 消费 Top 10（用户+金额）

**配置管理：**
- `get_config()` — 返回当前积分相关配置
- `update_config(key, value)` — 更新配置（通过修改 settings 对象的属性，运行时生效）

### API 路由

| Method | Path | 认证 | 说明 |
|--------|------|------|------|
| GET | `/api/admin/dashboard` | admin | 数据看板 |
| GET | `/api/admin/packages` | admin | 套餐列表（含已下架） |
| POST | `/api/admin/packages` | admin | 创建套餐 |
| PUT | `/api/admin/packages/{id}` | admin | 修改套餐 |
| DELETE | `/api/admin/packages/{id}` | admin | 删除套餐 |
| GET | `/api/admin/users` | admin | 用户列表（分页+搜索） |
| PUT | `/api/admin/users/{id}/credits` | admin | 调整积分 |
| PUT | `/api/admin/users/{id}/status` | admin | 禁用/启用 |
| GET | `/api/admin/config` | admin | 获取积分配置 |
| PUT | `/api/admin/config` | admin | 更新积分配置 |

### Schema（schemas/admin.py）

```python
# 套餐管理
class PackageCreateRequest(BaseModel):
    name: str
    price_cents: int
    credits: int
    bonus_credits: int = 0
    sort_order: int = 0
    is_active: bool = True

class PackageUpdateRequest(BaseModel):
    name: str | None = None
    price_cents: int | None = None
    credits: int | None = None
    bonus_credits: int | None = None
    sort_order: int | None = None
    is_active: bool | None = None

# 用户管理
class UserListQuery(BaseModel):
    search: str | None = None
    page: int = 1
    size: int = 20

class AdminUserResponse(BaseModel):
    id: int
    phone: str
    nickname: str
    is_active: bool
    created_at: datetime
    credit_balance: int
    total_recharged: int
    total_consumed: int

class AdjustCreditsRequest(BaseModel):
    amount: int          # 正数加，负数减
    remark: str = "管理员调整"

class SetUserStatusRequest(BaseModel):
    is_active: bool

# 看板
class DashboardResponse(BaseModel):
    total_users: int
    total_revenue_cents: int
    total_credits_granted: int
    total_credits_consumed: int
    today_new_users: int
    top_recharge_users: list[TopUserEntry]
    top_consume_users: list[TopUserEntry]

class TopUserEntry(BaseModel):
    user_id: int
    nickname: str
    phone: str
    amount: int

# 配置
class ConfigResponse(BaseModel):
    credits_per_token: float
    new_user_bonus_credits: int

class ConfigUpdateRequest(BaseModel):
    credits_per_token: float | None = None
    new_user_bonus_credits: int | None = None
```

## 前端设计

### 路由与导航

**AppLayout 改造：** 检查 `user.is_admin`，超管时显示"管理"菜单项。

```
/admin/dashboard    — AdminDashboard.tsx  数据看板
/admin/packages     — AdminPackages.tsx   套餐管理
/admin/users        — AdminUsers.tsx      用户管理
/admin/config       — AdminConfig.tsx     积分配置
```

### 新增前端文件

| 操作 | 路径 | 职责 |
|------|------|------|
| Create | `web/frontend/src/api/admin.ts` | 管理 API 调用 |
| Create | `web/frontend/src/pages/admin/AdminDashboard.tsx` | 数据看板 |
| Create | `web/frontend/src/pages/admin/AdminPackages.tsx` | 套餐管理 |
| Create | `web/frontend/src/pages/admin/AdminUsers.tsx` | 用户管理 |
| Create | `web/frontend/src/pages/admin/AdminConfig.tsx` | 积分配置 |
| Modify | `web/frontend/src/components/AppLayout.tsx` | 超管菜单 |
| Modify | `web/frontend/src/App.tsx` | 注册 admin 路由 |
| Modify | `web/frontend/src/api/client.ts` | 响应拦截器处理 403 |

### 数据看板页面

- 顶部 5 个 Statistic 卡片：总用户、总收入、总发放、总消费、今日新增
- 下方两列：充值 Top 10 表格 + 消费 Top 10 表格

### 套餐管理页面

- Ant Design Table 展示所有套餐（含已下架，灰色标记）
- 操作列：编辑（Modal）、上下架（Switch）、删除（确认弹窗）
- 顶部"新增套餐"按钮

### 用户管理页面

- 搜索框（手机号/昵称）
- Table 列：ID、手机号、昵称、积分余额、累计充值、累计消费、状态、操作
- 操作列：调整积分（Modal + 输入金额+备注）、禁用/启用（确认弹窗）

### 积分配置页面

- 表单：每 Token 积分价格、新人赠送积分
- 保存按钮 + 成功提示

## 不在 P2.5 范围内

- 多角色/权限系统（只做超管+普通用户）
- 操作审计日志
- 文件管理
- 退款/冲正
- 微信支付

## 依赖

- 无新依赖，复用现有 FastAPI + SQLAlchemy + Ant Design 技术栈

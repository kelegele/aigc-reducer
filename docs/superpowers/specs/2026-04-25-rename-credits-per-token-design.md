# 重命名 CREDITS_PER_TOKEN → CREDITS_PER_1K_TOKENS

## 动机

`CREDITS_PER_TOKEN` 名称有误导性。公式为 `token_count / 1000 * CREDITS_PER_TOKEN`，实际含义是"每 1000 token 消耗多少积分"，但变量名暗示的是"每个 token"。

## 方案

将所有 `credits_per_token` / `CREDITS_PER_TOKEN` 重命名为 `credits_per_1k_tokens` / `CREDITS_PER_1K_TOKENS`。公式逻辑不变，仅改变量名和 DB key。

## 改动范围

### 后端

| 文件 | 改动 |
|------|------|
| `config.py` | `CREDITS_PER_TOKEN` → `CREDITS_PER_1K_TOKENS`，注释更新 |
| `services/credit.py` | `settings.CREDITS_PER_TOKEN` → `settings.CREDITS_PER_1K_TOKENS`，docstring 更新 |
| `services/reduce.py` | `settings.CREDITS_PER_TOKEN` → `settings.CREDITS_PER_1K_TOKENS` |
| `services/admin.py` | `_CONFIG_MAP` key 和属性名更新，函数参数名更新 |
| `schemas/admin.py` | `credits_per_token` → `credits_per_1k_tokens` |
| `routers/admin.py` | `req.credits_per_token` → `req.credits_per_1k_tokens` |

### 数据库

- `system_config` 表：UPDATE key `credits_per_token` → `credits_per_1k_tokens`
- 无需 Alembic 迁移（表结构未变），通过启动脚本或手动 SQL 执行

### 前端

| 文件 | 改动 |
|------|------|
| `api/admin.ts` | interface 字段 `credits_per_token` → `credits_per_1k_tokens` |
| `pages/admin/AdminConfig.tsx` | form field name 和 label 更新 |

### 环境变量

| 文件 | 改动 |
|------|------|
| `.env.example` | `CREDITS_PER_TOKEN` → `CREDITS_PER_1K_TOKENS` |
| `web/.env.example` | 同上 |

### 测试

所有测试文件中的变量名和 DB key 同步更新，数值和断言不变。

### 文档

`CLAUDE.md` 中所有 `CREDITS_PER_TOKEN` / `credits_per_token` 引用同步更新。

## 验证

1. `cd web && uv run pytest tests/ -v` — 154 测试全部通过
2. 管理后台配置页面正常读写
3. 重启后 DB 配置正确加载

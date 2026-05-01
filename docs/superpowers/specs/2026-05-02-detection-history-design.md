# 检测历史功能设计

## Context

P3 检测/改写功能已上线，用户可以创建任务并逐步完成检测和改写。但 `/history` 页面目前是空壳（显示"检测功能开发中"），用户无法查看历史任务列表和已完成的比对结果。本功能补全这个缺口。

## 需求

1. 历史页面展示用户所有 Reduce 任务，支持按状态筛选（全部/进行中/已完成/失败）和标题搜索
2. 已完成/失败的任务点击进入 TaskWorkspace 只读查看（原文 vs 改写结果）
3. 进行中的任务点击进入 TaskWorkspace 继续操作
4. TaskWorkspace 只读模式下支持复制全文

## 改动范围

### 后端

**`web/src/aigc_web/services/reduce.py`** — `list_tasks` 方法新增 `status` 和 `keyword` 参数：
- `status`：直接传任务状态值。`in_progress` 为特殊值，过滤 `status NOT IN ("completed", "failed")`
- `keyword`：`title ILIKE '%keyword%'` 模糊搜索
- 两者可组合使用，均为 optional

**`web/src/aigc_web/routers/reduce.py`** — `list_tasks` 路由新增查询参数 `status: str | None = None` 和 `keyword: str | None = None`，透传给 service。

Schema 不变，`TaskListResponse` 结构不变。

### 前端

**`web/frontend/src/api/reduce.ts`** — `getTasks` 函数扩展：
```typescript
export async function getTasks(params: {
  page?: number;
  page_size?: number;
  status?: string;
  keyword?: string;
}): Promise<TaskListResponse>
```

**`web/frontend/src/pages/History.tsx`** — 重写为完整历史列表页：
- 顶部：`Select` 状态筛选（全部 / 进行中 / 已完成 / 失败）+ `Input.Search` 搜索框
- 中部：`List` 组件展示任务行，每行显示标题、状态 `Tag`、创建时间、消耗积分
- 底部：分页器
- 筛选/搜索变更时重置到第 1 页并重新请求
- 点击任务跳转 `/reduce/:taskId`
- 空状态用 `Empty` 组件

**`web/frontend/src/pages/reduce/TaskWorkspace.tsx`** — 增加只读模式：
- 当 `task.status` 为 `completed` 或 `failed` 时，设 `isReadonly = true`
- 只读模式下：隐藏所有操作按钮（检测、改写、确认段落等），展示原文 vs 最终文本对比
- 保留「复制全文」按钮，复制 `reduced_text` 或段落 `final_text` 拼接
- 进行中的任务保持现有交互逻辑不变

## 不在本期范围

- 导出文档（DOCX 下载）— 另外在开发中
- 任务删除
- 管理后台的历史查看

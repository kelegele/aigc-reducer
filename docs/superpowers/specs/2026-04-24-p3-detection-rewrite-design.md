# P3 设计文档：检测/改写 Web 服务

> 日期：2026-04-24
> 状态：设计中

## Context

P1/P2 已完成 Web 服务骨架、用户认证、积分充值与支付系统。P3 的核心是将 CLI 的 AIGC 检测/改写能力封装为 Web 服务，用户通过前端上传论文、交互式完成检测和改写，按 token 消耗积分。

CLI 核心模块（parser、detector、rewriter、styles、llm_client）已完整实现，需要从 CLI 包中提取为独立的共享核心包，供 CLI 和 Web 共同依赖。

---

## 1. 需求决策汇总

| 决策项 | 选择 |
|--------|------|
| 交互模式 | 逐步交互式 |
| 段落确认方式 | 向导式 + 列表模式可切换 |
| 输入格式 | docx + pdf + 纯文本粘贴 |
| 结果存储 | 保存为历史记录（不可继续编辑） |
| 检测模式 | 用户自选 rules / llm |
| 全量语义重构 | 保留，作为可选步骤 |
| 改写风格 | 全文统一风格 |
| 改写生成策略 | 用户选全量生成 or 逐段生成 |
| 积分扣费 | rules 检测免费；llm 检测、全量重构、改写均需预检 + 按实际扣费 |
| 输出方式 | 在线对比视图（可复制）+ docx 下载 |
| 代码共享 | 方案 B：提取核心为独立共享包，放在项目根目录 |

---

## 2. 整体架构

### 2.1 目录结构

```
aigc-reducer/                  # 项目根目录
├── core/                      # 新增：共享核心包
│   ├── pyproject.toml         # 独立包：aigc-reducer-core
│   ├── src/
│   │   └── aigc_reducer_core/
│   │       ├── __init__.py
│   │       ├── parser.py
│   │       ├── detector.py
│   │       ├── rewriter.py
│   │       ├── llm_client.py  # LLM 配置通过构造函数传入，不依赖环境变量
│   │       ├── detectors/
│   │       ├── styles/
│   │       └── data/
│   └── tests/                 # 核心包独立测试
├── cli/                       # CLI 工具（依赖 core）
│   ├── pyproject.toml         # dependencies: ["aigc-reducer-core"]
│   └── src/
│       └── aigc_reducer/
│           ├── cli.py         # CLI 交互逻辑
│           └── report.py      # Rich 终端输出
├── web/                       # Web 服务（依赖 core）
│   ├── pyproject.toml         # dependencies: ["aigc-reducer-core", ...]
│   └── src/
│       └── aigc_web/
└── docs/
```

### 2.2 核心包改造要点

#### 2.2.1 LLMClient — 配置通过构造函数传入

LLM 配置（model、api_key、base_url）全部通过 `LLMClient.__init__()` 传入，不读环境变量：

```python
class LLMClient:
    def __init__(self, model: str, api_key: str, base_url: str | None = None):
        self.model = model
        self.api_key = api_key
        self.base_url = base_url

    @classmethod
    def from_env(cls) -> "LLMClient":
        """CLI 兼容：从环境变量读取配置"""
        return cls(
            model=os.environ["LLM_MODEL"],
            api_key=os.environ["LLM_API_KEY"],
            base_url=os.environ.get("LLM_BASE_URL"),
        )
```

CLI 仍可用 `LLMClient.from_env()`，Web 直接传参构造。

#### 2.2.2 RewriteStyle — 接受 LLMClient 注入

```python
class RewriteStyle(ABC):
    def __init__(self, llm_client: LLMClient):
        self._llm_client = llm_client

    def _call_llm(self, prompt: str) -> str:
        return self._llm_client.chat(prompt)
```

`LLMDetector` 同理。

#### 2.2.3 数据文件路径

`ConnectorDetector` 改用 `importlib.resources`：

```python
import importlib.resources
data_path = importlib.resources.files("aigc_reducer_core") / "data" / "ai_connectors.yaml"
```

`pyproject.toml` 添加 `[tool.setuptools.package-data]` 包含 `data/*.yaml`。

#### 2.2.4 取消支持

`AIGCDetector` 和 `Rewriter` 的循环中加入取消检查点：

```python
class AIGCDetector:
    def __init__(self, mode="rules", cancel_event: threading.Event | None = None):
        self._cancel = cancel_event

    def analyze_all(self, paragraphs):
        results = []
        for p in paragraphs:
            if self._cancel and self._cancel.is_set():
                raise CancelledError()
            results.append(self.analyze(p))
        return results
```

### 2.3 异步兼容

不改动核心包同步代码，Web service 层用 `asyncio.to_thread()` 包装：

```python
async def run_detection(detector, paragraphs):
    return await asyncio.to_thread(detector.analyze_all, paragraphs)
```

### 2.4 Web 配置新增

`config.py` 添加 LLM 配置：

```python
LLM_MODEL: str = ""
LLM_API_KEY: str = ""
LLM_BASE_URL: str | None = None
```

`.env.example` 同步添加这三项 + `CREDITS_PER_TOKEN` 和 `NEW_USER_BONUS_CREDITS`。

---

## 3. 数据模型

### 3.1 新增表 `reduction_tasks`

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer PK | 自增主键 |
| user_id | FK → users | 所属用户 |
| title | String(200) | 文档标题（文件名或首段标题） |
| status | String(20) | `parsing` → `detecting` → `reconstructing` → `rewriting` → `completed` / `failed` |
| detect_mode | String(10) | `rules` 或 `llm` |
| style | String(20) | 改写风格名称 |
| full_reconstruct | Boolean | 是否执行了全量重构 |
| original_text | Text | 原始全文 |
| reduced_text | Text | 改写后全文（最终结果） |
| total_tokens | Integer | LLM 总消耗 token |
| total_credits | Integer | 总消耗积分（分） |
| created_at | DateTime | 创建时间 |
| completed_at | DateTime | 完成时间 |

### 3.2 新增表 `reduction_paragraphs`

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer PK | 自增主键 |
| task_id | FK → reduction_tasks | 所属任务（级联删除） |
| index | Integer | 段落序号 |
| original_text | Text | 原文 |
| is_heading | Boolean | 是否为标题 |
| has_formula | Boolean | 是否包含公式 |
| has_code | Boolean | 是否包含代码块 |
| detection_result | JSON | 各维度分数、风险等级、AI 特征 |
| risk_level | String(10) | 低/中/中高/高 |
| needs_processing | Boolean | 是否需要改写 |
| rewrite_aggressive | Text | 激进版改写 |
| rewrite_conservative | Text | 保守版改写 |
| user_choice | String(20) | `aggressive` / `conservative` / `original` / `manual` |
| manual_text | Text | 手动输入文本（choice=manual 时） |
| final_text | Text | 最终采用的文本 |
| status | String(20) | `pending` / `detected` / `rewritten` / `confirmed` |

### 3.3 索引

- `reduction_paragraphs(task_id, index)` — 按任务查段落
- `reduction_tasks(user_id, created_at)` — 用户历史列表排序

---

## 4. API 端点

所有端点前缀 `/api/reduce`，需认证（`get_current_user` 依赖）。

| Method | Path | 说明 |
|--------|------|------|
| POST | `/tasks` | 创建任务（multipart: file 或 json: text + detect_mode + style） |
| GET | `/tasks` | 用户任务列表（分页） |
| GET | `/tasks/:id` | 任务详情（含所有段落） |
| POST | `/tasks/:id/estimate` | 预估积分消耗（不执行，只返回预估值） |
| POST | `/tasks/:id/detect` | 启动检测（SSE streaming response） |
| POST | `/tasks/:id/reconstruct` | 全量语义重构（SSE streaming，可选） |
| POST | `/tasks/:id/rewrite` | 启动改写（SSE streaming，query: mode=batch/sequential） |
| PUT | `/tasks/:id/paragraphs/:index/choice` | 确认某段选择 |
| POST | `/tasks/:id/finalize` | 所有段落确认后生成最终文档 |
| GET | `/tasks/:id/download` | 下载 docx |

### 4.1 SSE 事件格式

**检测 SSE**（`POST /detect`，streaming response）：

```
event: progress
data: {"current": 3, "total": 20}

event: paragraph_done
data: {"index": 3, "risk_level": "中高", "composite_score": 45.2}

event: complete
data: {"total_paragraphs": 20, "needs_processing": 8}

event: error
data: {"message": "积分不足，预计需要 500 积分"}
```

**改写 SSE**（`POST /rewrite`）：

```
event: progress
data: {"current": 5, "total": 8}

event: paragraph_ready
data: {"index": 5, "aggressive": "...", "conservative": "..."}

event: complete
data: {"total_credits_used": 350}

event: error
data: {"message": "..."}
```

---

## 5. 积分扣费流程

所有涉及 LLM 的操作统一遵循：**预估 → 提示用户 → 校验余额 → 执行 → 按实际扣费**

| 步骤 | 消耗 LLM | 预检逻辑 |
|------|---------|---------|
| 解析文件 | 否 | 无 |
| rules 检测 | 否 | 无 |
| llm 检测 | 是 | 预估全文 token → 换算积分 → 提示用户 → 校验余额 |
| 全量语义重构 | 是 | 预估全文 token → 换算积分 → 提示用户 → 校验余额 |
| 改写（全量模式） | 是 | 预估所有需处理段落 token → 一次性校验 |
| 改写（逐段模式） | 是 | 每段生成前单独预估 + 校验 |
| 用户确认选择 | 否 | 无 |
| 生成最终文档 | 否 | 无 |

**预估算逻辑**：中文 1 字 ≈ 1.5 token 估算输入，加上固定 prompt 开销估算输出 token。

**扣费时机**：每步 LLM 操作完成后按实际 token 调用 `credit_service.consume()`，写流水 `ref_type = "reduction_task"`。

**失败处理**：如果中途余额不足，任务标记 `failed`，已完成的段落结果保留。

---

## 6. 前端设计

### 6.1 页面结构

```
pages/
├── reduce/
│   ├── NewTask.tsx        # /reduce/new
│   └── TaskWorkspace.tsx  # /reduce/:taskId
├── History.tsx            # 历史记录列表（已有，适配 P3 数据）
```

### 6.2 新建任务页（`/reduce/new`）

左右分栏布局：
- **左侧**：文件上传区（拖拽 .docx/.pdf）或文本粘贴区，二选一
- **右侧**：
  - 检测模式选择：卡片式，图标 + 特性标签（免费/消耗积分/秒级完成/更精准），LLM 模式带"推荐"角标
  - 改写风格选择：卡片网格，每张卡片内嵌改写示例预览，选中态边框高亮
  - "开始检测"按钮

### 6.3 任务工作区（`/reduce/:taskId`）

一个页面内完成全流程，顶部 Steps 条标识当前阶段。

**步骤 ① 解析**（自动，status: `parsing`）

**步骤 ② 检测**（status: `detecting`）
- SSE 进度条 + 段落列表实时着色（绿/黄/红）
- 完成后展示总览统计：X 段低风险 / Y 段需处理
- 提供"全量语义重构"按钮（可选步骤）

**步骤 ③ 全量重构**（可选，status: `reconstructing`）
- 点击后弹出积分预估确认框
- SSE 推进度

**步骤 ④ 改写**（status: `rewriting`）
- 用户选择改写模式：**全量生成** or **逐段生成**
- 全量模式：一次性生成所有 A/B（SSE 推进度），完成后审阅
- 逐段模式：循环 { SSE 推当前段 → 展示 A/B → 用户确认 → 扣费 → 下一段 }
- 审阅时支持 **向导模式** 和 **列表模式** 切换：
  - **向导模式**：聚焦当前段落，原文 + A/B 左右对比，选择后自动跳下一段
  - **列表模式**：所有段落一览，默认展开显示完整 A/B 方案；支持一键收起/展开、逐个收起/展开；提供"批量选 A"快捷操作
- 每段选择：方案 A（激进）/ 方案 B（保守）/ 保留原文 / 手动输入
- 每次选择调用 `PUT /paragraphs/:index/choice` 保存

**步骤 ⑤ 结果**（status: `completed`）
- 左右对比视图（原文 vs 改写后），同步滚动
- 改写段落用左侧色条标注（区分原风险等级）
- 两侧各有"复制全文"按钮，段落文本可单独选中复制
- 下载改写报告（DOCX）按钮
- 顶部统计：总段落数、改写数、消耗积分

### 6.4 历史记录

已有 `History.tsx` 页面适配 P3 数据，展示 `reduction_tasks` 列表。点击进入任务详情查看对比视图。

---

## 7. Web 服务新增层

### 7.1 Schemas（`schemas/reduce.py`）

```python
class TaskCreateRequest:
    source_type: Literal["file", "text"]
    text: str | None                    # source_type=text 时必填
    detect_mode: Literal["rules", "llm"]
    style: str

class ParagraphChoiceRequest:
    choice: Literal["aggressive", "conservative", "original", "manual"]
    manual_text: str | None             # choice=manual 时必填

class CreditsEstimateResponse:
    estimated_tokens: int
    estimated_credits: int
    current_balance: int
    sufficient: bool

class ParagraphResponse:
    index: int
    original_text: str
    is_heading: bool
    has_formula: bool
    has_code: bool
    risk_level: str | None
    composite_score: float | None
    detection_detail: dict | None
    rewrite_aggressive: str | None
    rewrite_conservative: str | None
    user_choice: str | None
    final_text: str | None
    status: str

class TaskResponse:
    id: int
    title: str
    status: str
    detect_mode: str
    style: str
    full_reconstruct: bool
    total_tokens: int
    total_credits: int
    original_text: str
    reduced_text: str | None
    created_at: str
    completed_at: str | None
    paragraphs: list[ParagraphResponse]

class TaskListItem:
    id: int
    title: str
    status: str
    style: str
    total_credits: int
    paragraph_count: int
    created_at: str
    completed_at: str | None
```

### 7.2 Service（`services/reduce.py`）

```python
class ReduceService:
    # 任务生命周期
    async def create_task(user_id, source_type, file/text, detect_mode, style)
    async def start_detection(task_id)
    async def start_reconstruction(task_id)
    async def start_rewrite(task_id, mode: "batch" | "sequential")
    async def confirm_paragraph(task_id, index, choice, manual_text)
    async def finalize_task(task_id)

    # 查询
    async def get_task(task_id, user_id)
    async def list_tasks(user_id, page, page_size)

    # 工具
    async def estimate_credits(task_id, operation: str) -> CreditsEstimateResponse
    async def download_docx(task_id) -> bytes
```

### 7.3 集成点

```
ReduceService
  ├── credit_service.consume()              — 每步 LLM 操作后扣费
  ├── credit_service.get_balance()          — 预检余额
  ├── aigc_reducer_core.parser              — 解析文件
  ├── aigc_reducer_core.detector            — 检测
  ├── aigc_reducer_core.rewriter            — 改写
  └── aigc_reducer_core.llm_client.LLMClient — 从 config.py 配置构造单例
```

---

## 8. 关键技术细节

### 8.1 并发处理

- 核心包同步代码通过 `asyncio.to_thread()` 在线程池中执行，不阻塞 FastAPI 事件循环
- `LLMClient` 单例注入，避免每次调用重建实例
- 规则检测器纯计算，天然线程安全
- litellm 支持并发调用

### 8.2 文件上传处理

- multipart upload，后端收到后解析为段落存入数据库
- 文件内容解析后原文存入 `reduction_tasks.original_text`
- 不保留原始文件，解析完成后丢弃

### 8.3 DOCX 改写报告生成

导出的不是简单改写后文档，而是一份**改写报告**，包含完整的分析过程和结果。

**报告结构**：

```
一、任务概要
  - 检测模式（Rules / LLM）
  - 改写风格
  - 是否执行全量语义重构
  - 总段落数 / 需改写数 / 保留数

二、逐段分析（仅 needs_processing 的段落）
  每段包含：
  - 段落序号 + 风险等级 + 综合分
  - 原文摘要（段首句 + ... + 段末句）
  - 风险分析：各维度分数（困惑度、突发性、连接词、认知特征、语义指纹）及解读
  - AI 特征描述列表
  - 用户选择的改写方案（激进/保守/原文/手动）
  - 改写后文本

三、完整改写后全文
  拼接所有段落的 final_text，改写过的段落用高亮/色块标注，与未改写段落（保留原文）视觉区分，用户一目了然哪些内容经过了改写。
```

**实现**：使用 `python-docx` 生成，自定义标题、正文、引用块样式。

---

## 9. 核心包提取迁移计划

### 9.1 迁移步骤

1. 创建 `core/` 目录结构 + `pyproject.toml`（包名 `aigc-reducer-core`）
2. 将 `cli/src/aigc_reducer/` 下的核心模块移动到 `core/src/aigc_reducer_core/`：
   - `parser.py`、`detector.py`、`rewriter.py`、`llm_client.py`
   - `detectors/`、`styles/`、`data/`
3. 改造 `llm_client.py`：LLM 配置通过构造函数传入，`from_env()` 保留为 CLI 兼容类方法
4. 改造 `styles/base.py`：`RewriteStyle.__init__` 必须接收 `llm_client`（不再默认 `from_env`）
5. 改造 `ConnectorDetector`：数据路径改用 `importlib.resources`
6. 添加取消支持到 `AIGCDetector` 和 `Rewriter`
7. 核心包的测试从 `cli/tests/` 拆分到 `core/tests/`
8. 更新 `cli/pyproject.toml`：`dependencies = ["aigc-reducer-core"]`，删除已移入核心的依赖
9. 更新 `web/pyproject.toml`：添加 `aigc-reducer-core` 依赖
10. 更新 CLI 的 import 路径：`from aigc_reducer_core.xxx import ...`

### 9.2 回归测试

| 改造项 | 影响范围 | 现有测试是否受影响 |
|--------|---------|------------------|
| 包名变更 `aigc_reducer` → `aigc_reducer_core` | 所有 import 语句 | 是，需更新 import |
| LLMClient 构造函数参数 | `RewriteStyle`、`LLMDetector` | CLI 测试需用 `from_env()` 构造 |
| 数据路径 importlib | `ConnectorDetector` | 需验证数据文件可找到 |
| 取消支持 | `AIGCDetector`、`Rewriter` | 否（默认 None） |

**回归步骤**：
1. `cd core && uv run pytest tests/ -v` — 核心包测试通过
2. `cd cli && uv run pytest tests/ -v` — CLI 测试通过（import 路径已更新）
3. `uv run aigc-reduce` — CLI 端到端验证

### 9.3 新增测试

| 测试 | 验证点 |
|------|--------|
| `test_llm_client_injection` | `RewriteStyle(llm_client=mock_client)` 使用注入的 client |
| `test_llm_client_from_env` | `LLMClient.from_env()` 从环境变量构造 |
| `test_connector_detector_data_path` | `ConnectorDetector` 在 pip install 后能找到数据文件 |
| `test_detector_cancel` | `cancel_event` 设置后 `analyze_all` 中断 |
| `test_rewriter_cancel` | `cancel_event` 设置后 `rewrite_all` 中断 |

---

## 10. Web 服务测试计划

### 10.1 测试基础设施

沿用现有模式（`web/tests/conftest.py`）：
- SQLite 内存数据库
- `TestClient` 做 API 集成测试
- `app.dependency_overrides[get_db]` 替换数据库

### 10.2 新增测试挑战及解决

| 挑战 | 解决方案 |
|------|---------|
| **LLM 调用** | Mock `LLMClient.chat()` 返回固定文本；规则检测器（纯计算）不需要 mock |
| **SSE 流式响应** | `TestClient` 支持 `with client.stream("POST", ...) as response` 逐行读取 SSE 事件 |

#### LLM Mock 策略

```python
# conftest.py 新增 fixture
@pytest.fixture
def mock_llm_client():
    client = MagicMock(spec=LLMClient)
    client.chat.return_value = "这是 mock 的改写结果文本。"
    return client

@pytest.fixture
def mock_llm_detector_response():
    return json.dumps({"score": 50, "risk_level": "中风险", "ai_features": ["模板化论证"]})
```

#### SSE 测试写法

```python
def test_detect_sse(client, auth_headers):
    with client.stream("POST", f"/api/reduce/tasks/{task_id}/detect", headers=auth_headers) as response:
        events = []
        for line in response.iter_lines():
            if line.startswith("data:"):
                events.append(json.loads(line[5:]))
    assert any(e.get("type") == "complete" for e in events)
```

### 10.3 后端测试文件

| 文件 | 覆盖内容 |
|------|---------|
| `test_reduce_api.py` | 任务 CRUD + 段落选择 + finalize + download 端点 |
| `test_reduce_service.py` | ReduceService 业务逻辑：积分预检/扣费、状态流转、余额不足失败、cancel |
| `test_reduce_sse.py` | SSE 流式响应：detect / rewrite / reconstruct 的进度事件格式 |

### 10.4 Service 层测试关键场景

```
test_create_task_from_file          — 上传 docx，解析为段落，创建任务
test_create_task_from_text          — 纯文本粘贴，解析为段落
test_detect_rules_mode             — rules 模式检测，不消耗积分
test_detect_llm_mode_insufficient  — llm 模式余额不足，拒绝启动
test_detect_llm_mode_success       — llm 模式检测成功，扣费
test_reconstruct_insufficient      — 全量重构余额不足
test_reconstruct_success           — 全量重构成功，扣费
test_rewrite_batch_mode            — 全量改写，一次性生成所有 A/B
test_rewrite_sequential_mode       — 逐段改写，逐段扣费
test_rewrite_sequential_insufficient_midway — 逐段改写中途余额不足，任务 failed
test_confirm_paragraph_choice      — 确认段落选择（A/B/原文/手动）
test_finalize_task                 — 所有段落确认后生成最终文档
test_cancel_task                   — 取消正在进行的任务
test_list_tasks_pagination         — 任务列表分页
```

### 10.5 开发阶段手动测试流程

后端和前端开发完成后，按以下步骤手动验证：

1. **环境准备**：启动后端 `uv run uvicorn` + 前端 `npm run dev`，确保 `.env` 配置了 `LLM_MODEL` 和 `LLM_API_KEY`
2. **完整流程**：
   - 登录 → 充值积分（或用管理员手动充值）
   - 访问 `/reduce/new`，上传一个 docx 文件，选 rules 检测 + 学术人文化
   - 验证解析 → 检测进度条 → 检测结果着色
   - 跳过全量重构
   - 选全量改写 → 等 A/B 生成完 → 向导模式逐段确认
   - 切换到列表模式验证批量操作
   - 查看结果对比页 → 复制文本 → 下载 docx
3. **积分边界**：余额为 0 时尝试 llm 检测，验证拒绝提示
4. **历史记录**：返回 `/history`，验证能看到刚完成的任务，点击可查看详情
5. **深色/浅色主题**：切换主题，验证所有 P3 页面样式跟随

---

## 11. 待后续迭代

- Rules 检测模式需持续优化准确率（已记录为 Tech Debt）
- P3 上线后根据用户反馈调整积分定价

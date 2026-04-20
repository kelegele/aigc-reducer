# AIGC Reducer

降低学术论文 AIGC 查重率的 CLI 工具。支持 LLM 反查检测和多种改写风格，帮助降低知网、GoCheck 等商业平台的 AI 查重率。

## 功能

- **双模式检测**：规则引擎（快速）或 LLM 反查（精准，模拟商业平台判断）
- **5 种改写风格**：学术人文化、口语化、文言文化、中英混杂化、粗犷草稿风
- **多格式输入**：`.docx` / `.doc` / `.pdf` / `.md`
- **多 LLM 供应商**：DeepSeek、通义千问、智谱、OpenAI、Anthropic 等（基于 LiteLLM）
- **交互式逐段确认**：每个高风险段落提供 A/B 两种改写方案，手动选择或跳过
- **全量语义重构**：可选打散全文骨架并重建逻辑

## 目录结构

```
aigc-reducer/
├── raw-paper/          # 原始论文文件（自动备份）
├── md-paper/           # 解析后的纯文本 md
├── output/             # 最终输出
│   ├── *_reduced.md          # 改写后全文
│   ├── *_diff.md             # 前后差异对比
│   └── *_revision_report.md  # 整改建议报告
├── src/aigc_reducer/   # 源代码
└── tests/              # 测试
```

## 快速开始

### 安装

```bash
cd aigc-reducer
uv sync
```

### 配置

创建 `.env` 文件：

```env
LLM_MODEL=openai/glm-5.1
LLM_API_KEY=your-api-key
LLM_BASE_URL=https://open.bigmodel.cn/api/coding/paas/v4
```

常用供应商配置示例：

| 供应商 | LLM_MODEL | LLM_BASE_URL |
|--------|-----------|--------------|
| 智谱 | `openai/glm-5.1` | `https://open.bigmodel.cn/api/coding/paas/v4` |
| DeepSeek | `deepseek/deepseek-chat` | 无需配置 |
| 通义千问 | `qwen/qwen-plus` | 无需配置 |
| OpenAI | `openai/gpt-4o` | 无需配置 |

### 运行

```bash
uv run aigc-reduce
```

按提示操作：选择文件 → 选择改写风格 → 选择检测模式 → 查看报告 → 逐段确认改写。

## 检测维度

| 维度 | 权重 | 说明 |
|------|------|------|
| 困惑度 | 20% | 用词是否过于标准化 |
| 突发性 | 20% | 句式长度是否高度统一 |
| 模板化连接词 | 20% | 是否高频使用"首先/其次/此外"等 |
| 认知特征 | 20% | 是否缺乏批判性观点 |
| 语义指纹 | 20% | 语义组织是否符合 AI 论证结构 |

## 技术栈

- Python 3.13 + uv
- LiteLLM（统一多供应商 LLM 接口）
- Rich（CLI 交互界面）
- python-docx / pdfplumber / mammoth（文档解析）

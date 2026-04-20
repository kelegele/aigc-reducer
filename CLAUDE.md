# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AIGC Reducer — 降低学术论文 AIGC 查重率的 CLI 工具。通过检测 AI 写作特征并提供多种改写风格，降低知网、GoCheck 等平台的 AI 查重率。

## Monorepo Structure

- `cli/` — 主应用（Python CLI 工具），所有源码、测试、依赖配置均在此目录下
- `docs/superpowers/` — 设计文档和实现计划

## Development Commands

All commands run from `cli/` directory:

```bash
# 安装依赖
uv sync

# 运行 CLI
uv run aigc-reduce

# 运行测试
uv run pytest tests/

# 运行测试（带覆盖率）
uv run pytest tests/ --cov=aigc_reducer

# 运行单个测试文件
uv run pytest tests/test_detector.py

# 运行单个测试用例
uv run pytest tests/test_detector.py::test_function_name -v
```

## Architecture

### 6-Step Interactive Workflow (cli.py)

输入文件 → 解析为段落 → 选择风格+检测模式 → 扫描风险 → (可选)全量语义重构 → 逐段 A/B 改写确认 → 输出三文件

### Core Components

- **parser.py** — 文档解析器，支持 .md/.docx/.doc/.pdf，输出 `Paragraph` dataclass 列表
- **detector.py** — 检测编排器，两种模式：
  - `rules` 模式：5 个规则检测器各 20% 权重求综合分
  - `llm` 模式：LLM 反查模拟商业平台判断
- **rewriter.py** — 改写编排器，管理 5 种风格的 aggressive/conservative 两档改写
- **llm_client.py** — LiteLLM 统一客户端，通过 `LLM_MODEL`/`LLM_API_KEY`/`LLM_BASE_URL` 环境变量配置
- **report.py** — Rich CLI 输出（扫描报告、进度、最终报告）

### Detection Modules (`detectors/`)

每个检测器独立实现，输入 `Paragraph`，输出 0-100 分：
- `perplexity.py` — 困惑度（用词标准化程度）
- `burstiness.py` — 突发性（句式长度方差）
- `connectors.py` — 模板化连接词频率
- `cognitive.py` — 认知特征（批判性思维标记）
- `semantic_fingerprint.py` — 语义指纹（AI 论证结构模式）
- `llm_detector.py` — LLM 反查（独立于上述 5 个，用于 llm 模式）

### Rewriting Styles (`styles/`)

所有风格继承 `base.py:RewriteStyle` 抽象类，实现 aggressive + conservative 两种 prompt：
- `academic_humanistic.py` — 学术人文化（默认推荐）
- `colloquial.py` — 口语化
- `classical.py` — 文言文化
- `mixed_en_zh.py` — 中英混杂化
- `rough_draft.py` — 粗犷草稿风

### Risk Levels

| 综合分 | 风险等级 |
|--------|---------|
| <10%   | 低风险   |
| 10-30% | 中风险   |
| 30-60% | 中高     |
| >60%   | 高风险   |

高于 30% 的段落会被标记为需处理。

## LLM Configuration

通过 `cli/.env` 文件配置（参考 `cli/.env.example`）。LLM 调用统一走 LiteLLM，模型标识格式为 `供应商/模型名`。`llm_client.py` 内置了各供应商默认 base_url，大部分情况只需配置 `LLM_MODEL` 和 `LLM_API_KEY`。

## Output Files

运行后在 `cli/output/` 生成三个文件：
- `*_reduced.md` — 改写后全文
- `*_diff.md` — 前后差异对比
- `*_revision_report.md` — 整改建议报告

## Key Patterns

- 所有 Python 操作通过 `uv`，不使用 pip/conda/venv
- Python >=3.10，使用 `str | None` 而非 `Optional[str]`
- 中文 docstring 和注释
- 检测器模块化：新增检测维度只需在 `detectors/` 下添加模块并在 `detector.py` 中注册
- 改写风格模块化：新增风格只需继承 `RewriteStyle` 并在 `rewriter.py` 中注册

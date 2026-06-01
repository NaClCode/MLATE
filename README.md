# MLATE — Multi-dimensional Literature Analysis and Thematic Exploration / 文献多维分析与主题探索

[English](#english) | [中文](#中文)

---

<a name="english"></a>

## English

MLATE (Multi-dimensional Literature Analysis and Thematic Exploration) is a full-process pipeline designed to transform raw literature CSV/Excel data into structured multi-dimensional labels using Large Language Models (LLMs).

### Core Workflow

```text
filter (LLM relevance scoring) → explore (Iterative sub-category discovery) → analyze (Multi-dim labeling) → retry (Error recovery)
```

### Installation

```bash
pip install -e .
```

### Quick Start

```bash
# 1. Topic Filtering: Score papers by relevance (1-5), filter ≥ 3
# Support WoS exported Excel files (.xls, .xlsx) directly
mlate filter --input savedrecs.xls --topic "large language model" --min-score 3 --output filtered.csv

# Note: Two files will be generated:
# 1. filtered.csv: Contains only papers with passed == True (relevance ≥ 3)
# 2. filtered_all.csv: Contains all papers with their relevance scores and reasons

# 2. Theme Exploration: Discover fine-grained sub-categories with optional researcher guidance
mlate explore --input filtered.csv --output taxonomy.json --batch-size 50 

# 3. Dimension Analysis: Perform two-level (Category + Sub-category) classification
mlate analyze --input filtered.csv --taxonomy taxonomy.json --output analyzed.csv

# 4. Error Retry: Automatically locate and retry 'ERROR' entries
mlate retry --input analyzed.csv

# Configuration Management
mlate config init                    # Initialize ~/.mlate/config.json
mlate config set api_base https://api.deepseek.com
mlate config set lang en             # Set output language (en/cn/both)
mlate config show                    # View effective configuration
```

### API Key Management

#### Security First
API Keys are **never stored locally** in configuration files to prevent security leaks.

#### Resolution Priority
```text
Environment Variables only (MLATE_API_KEY, etc.)
```

#### Environment Variables
```bash
# Recommended: Set for the current session, not persisted to disk
export MLATE_API_KEY=sk-xxx           # Linux/Mac
$env:MLATE_API_KEY="sk-xxx"           # Windows PowerShell
```

Supported environment variables (in order): `MLATE_API_KEY`, `LLM_API_KEY`, `OPENAI_API_KEY`, `DEEPSEEK_API_KEY`.

### Features

- **Adaptive Data Loading**: Supports CSV, Excel (`.xls`, `.xlsx`), and TSV files. Automatically detects and normalizes columns from sources like **Web of Science (WoS)** and **Scopus**.
- **Bilingual Logging**: Built-in logger supports English (default), Chinese, and bilingual (`both`) output. Toggle via `--lang` or `mlate config set lang`.
- **Refined Prompts**: Scientific prompts designed for sampling, scoring, taxonomy discovery, and evidence-based analysis.
- **Evidence-Based**: All classification results include "Evidence", "Refined Evidence", and "Reasoning" directly from the source text.

---

<a name="中文"></a>

## 中文

MLATE (Multi-dimensional Literature Analysis and Thematic Exploration) 是一个利用大语言模型（LLM）将原始文献 CSV/Excel 转化为结构化多维标注的全流程工具。

### 核心工作流

```text
filter（LLM 主题评分） → explore（批次发现子类） → analyze（逐篇标注） → retry（错误重测）
```

### 安装

```bash
pip install -e .
```

### 快速开始

```bash
# 1. 主题筛选：按主题相关性评分 (1-5)，筛选 ≥ 3 分的文献
# 直接支持 Web of Science 导出的 Excel 文件 (.xls, .xlsx)
mlate filter --input savedrecs.xls --topic "large language model" --min-score 3 --output filtered.csv

# 注：此命令会生成两个文件：
# 1. filtered.csv: 仅包含 passed == True (评分 ≥ 3) 的文献
# 2. filtered_all.csv: 包含全量评分数据，方便核对

# 2. 主题探索：从数据中自然发现分析维度与细分子类（支持通过 --guide 传入研究者引导词）
mlate explore --input filtered.csv --output taxonomy.json --batch-size 50 

# 3. 维度分析：基于探索出的体系执行两级分类标注
mlate analyze --input filtered.csv --taxonomy taxonomy.json --output analyzed.csv

# 4. 错误重试：自动定位标注失败的 ERROR 条目并重测
mlate retry --input analyzed.csv

# 配置管理
mlate config init                    # 初始化配置文件 ~/.mlate/config.json
mlate config set api_base https://api.deepseek.com
mlate config set lang cn             # 设置输出语言 (en/cn/both)
mlate config show                    # 查看当前生效配置
```

### API Key 管理

#### 安全第一
为了防止安全泄露，API Key **永远不会本地存储**在配置文件中。

#### 优先级
```text
仅支持环境变量 (MLATE_API_KEY 等)
```

#### 环境变量
```bash
# 推荐：仅当前会话有效，不持久化到磁盘
export MLATE_API_KEY=sk-xxx           # Linux/Mac
$env:MLATE_API_KEY="sk-xxx"           # Windows PowerShell
```

支持的环境变量（按顺序检测）：`MLATE_API_KEY`, `LLM_API_KEY`, `OPENAI_API_KEY`, `DEEPSEEK_API_KEY`。

### 功能特性

- **自适应数据加载**：支持 CSV、Excel (`.xls`, `.xlsx`) 及 TSV 文件。自动识别并归一化来自 **Web of Science (WoS)** 和 **Scopus** 等来源的列名。
- **双语日志系统**：内置 Logger 支持英文（默认）、中文及双语模式。可通过 `--lang` 参数或 `mlate config set lang` 切换。
- **精细化提示词**：针对样本探索、相关性评分、分类体系发现及证据提取进行了深度的 Prompt 工程优化。
- **证据导向**：所有分类标注均包含“依据”、“细化依据”和“逻辑理由”，确保结果可回溯、不凭空推测。

---

## CLI Parameters Reference / 命令行参数参考

### Global Options / 全局选项
| Parameter / 参数 | Description / 描述 | Default / 默认 |
|---|---|---|
| `--api-base` | LLM API Base URL. | Config / 配置文件 |
| `--model` | Model name (e.g., `deepseek-chat`). | Config / 配置文件 |
| `--workers` | Concurrent worker threads for LLM requests. | `8` |
| `--qps` | Maximum Queries Per Second to avoid rate limiting. | `2.0` |
| `--lang` | Output language: `cn` (Chinese), `en` (English), `both`. | `en` |
| `--source` | Data source type: `auto`, `wos`, `scopus`, `standard`. | `auto` |

### 1. `filter` (Relevance Scoring)
| Parameter / 参数 | Description / 描述 |
|---|---|
| `--input` | Path to raw literature file (Excel/CSV/TXT). |
| `--output` | Path to save the scored results (CSV). |
| `--topic` | Target research topic/keywords for relevance scoring. |
| `--min-score` | Minimum score (1-5) to mark as passed. |

### 2. `explore` (Taxonomy Discovery)
| Parameter / 参数 | Description / 描述 |
|---|---|
| `--input` | Path to filtered literature file (CSV). |
| `--output` | Path to save the generated `taxonomy.json`. |
| `--batch-size` | Number of papers per LLM batch for discovery. |
| `--guide` | Natural language instructions to guide the discovery. |
| `--max-papers`| (Optional) Limit the number of papers to analyze. |

### 3. `analyze` (Multi-dimensional Labeling)
| Parameter / 参数 | Description / 描述 |
|---|---|
| `--input` | Path to filtered literature file (CSV). |
| `--output` | Path to save the final labeled results (CSV). |
| `--taxonomy` | Path to the `taxonomy.json` generated in step 2. |
| `--max-papers`| (Optional) Limit the number of papers to analyze. |

### 4. `retry` (Error Recovery)
| Parameter / 参数 | Description / 描述 |
|---|---|
| `--input` | Path to the CSV file containing `ERROR` tags. |
| `--output` | (Optional) Path to save the fixed results. |

### 5. `config` (Configuration Management)
| Action / 动作 | Description / 描述 |
|---|---|
| `init` | Initialize configuration file at `~/.mlate/config.json`. |
| `set <key> <value>`| Set a config value (e.g., `set model gpt-4`). |
| `get <key>` | Get a specific config value. |
| `show` | Show all effective configurations (Key masked). |




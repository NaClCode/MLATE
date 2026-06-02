# MLATE — Multi-dimensional Literature Analysis and Thematic Exploration

MLATE is a CLI tool for literature deconstruction and taxonomy building using Large Language Models (LLMs). It assists researchers in extracting multi-dimensional features and organizing sub-categories from large bibliographic datasets.

[中文文档](#中文) | [English Documentation](#english-doc)

---

<a name="中文"></a>
## 🇨🇳 中文说明 (主要内容)

MLATE (Multi-dimensional Literature Analysis and Thematic Exploration) 是一个辅助研究者进行文献解构与分类体系构建的命令行工具。它利用大语言模型（LLM）自动化处理文献数据，协助研究者从海量文献中梳理研究维度并生成初步的学术分类。

### 🌟 主要功能
- **逐篇文献探索 (Discovery)**：对每篇文献独立进行特征提取与初步分类，旨在捕捉细节，减少大批量处理时的信息丢失与偏见。
- **两阶段收敛逻辑 (Convergence)**：将“原始多样化发现”与“分类体系收敛”分阶段。收敛过程基于语义相似与样本热度进行标签合并。
- **增量式迭代调优**：支持针对特定维度（如“应用场景”）反复调整收敛参数，系统会自动保护其他已处理维度的存量数据。
- **双分类标注体系**：最终生成的 CSV 报表同时保留 `原始标签` 与 `收敛后的大类`，方便研究者核对 AI 的分类演化逻辑。
- **自动化翻译支持**：内置翻译模块，支持利用 LLM 对文献标题、摘要及分类结果进行多语言转换。

### 📖 快速上手
```bash
# 1. 主题筛选：对文献进行相关性评分并剔除无关项
mlate filter --input data.xls --topic "知识图谱在工业中的应用" --output filtered.csv 

# 2. 逐篇探索：生成每篇文献的原始分类草案
mlate explore --input filtered.csv --output draft.json --dims "应用场景,技术路径"

# 3. 智能收敛：将琐碎标签合并为精炼的分类体系，并标注 CSV
mlate converge --input draft.json --output taxonomy.json \
  --output-csv final_result.csv --limit-cats 5 --source-csv filtered.csv

# 4. 自动化翻译：(可选) 翻译摘要、标题或分类标签
mlate translate --input final_result.csv --output final_en.csv --lang "English" \
  --cols "Title,Abstract,应用场景_category"
```

### � 命令行参数参考 (CLI Reference)

| 命令 | 参数 | 描述 |
| :--- | :--- | :--- |
| **全局选项** | `--model` | 指定模型名（如 `deepseek-chat`, `gpt-4o`）。 |
| | `--source` | 数据源格式 (`wos`, `scopus`, `standard`, `auto`)。 |
| **filter** | `--topic` | 用于相关性评分的主题关键词。 |
| | `--min-score` | 筛选阈值（1-5，默认 3.0）。分数越高筛选越严。 |
| | `--output-lang`| **(多语言)** 评分标准与理由的生成语言。 |
| **explore** | `--dims` | 初始探索维度（如：应用场景,技术路径）。 |
| | `--guide` | 研究者引导词，用于精细化控制 AI 探索方向。 |
| | `--output-lang`| **(多语言)** 原始标签与理由的生成语言。 |
| **converge** | `--limit-cats` | 每个维度最终保留的分类数量上限。 |
| | `--dims` | **(增量更新)** 仅对指定的维度进行收敛处理。 |
| | `--output-csv` | **(核心)** 生成带 `原始标签` 与 `收敛大类` 的标注文献库。 |
| | `--source-csv` | 原始 CSV 路径，用于将 ID 映射回论文标题。 |
| | `--output-lang`| **(多语言)** 分类定义与判定标准的生成语言。 |
| **translate**| `--lang` | 目标翻译语言（如 English, 中文）。 |
| | `--cols` | **(CSV专用)** 指定需要翻译的列名（逗号分隔）。 |
| **config** | `set/show` | 管理全局配置（如默认模型、输出语言、日志级别）。 |

### � 安全与配置
- **API Key**：出于安全考虑，系统仅支持通过环境变量（如 `MLATE_API_KEY`）获取 Key，禁止本地存储。
- **全局语言配置**：
  ```bash
  # 设置 LLM 产出内容的默认语言 (如 English, 中文)
  mlate config set output_lang English
  ```

---

<a name="english-doc"></a>
## 🇬🇧 English Documentation (Translated)

MLATE (Multi-dimensional Literature Analysis and Thematic Exploration) is a CLI tool designed to assist researchers in literature deconstruction and taxonomy building. It leverages Large Language Models (LLMs) to automate bibliographic data processing, helping researchers identify research dimensions and generate initial academic classifications from large datasets.

### 🚀 Key Features
- **One-by-One Discovery**: Extracts features and initial categories for each paper independently to capture fine details and reduce information loss or bias common in batch processing.
- **Two-Phase Convergence**: Decouples "spontaneous discovery" from "taxonomy convergence." The convergence process merges labels based on semantic similarity and sample popularity.
- **Incremental Iterative Tuning**: Supports repeated adjustment of convergence parameters for specific dimensions (e.g., "Application") while protecting existing data in other processed dimensions.
- **Dual-Category Labeling**: The final CSV report includes both `raw_labels` and `converged_categories`, allowing researchers to verify the AI's classification evolution logic.
- **Automated Translation Support**: Built-in translation module to convert paper titles, abstracts, and categories across multiple languages using LLMs.

### 📖 Quick Start
```bash
# 1. Filter: Score relevance and remove noise
mlate filter --input data.xls --topic "..." --output filtered.csv 

# 2. Explore: Generate raw classification drafts for each paper
mlate explore --input filtered.csv --output draft.json --dims "Application,Technology"

# 3. Converge: Merge trivial labels into a clean taxonomy and label the CSV
mlate converge --input draft.json --output taxonomy.json \
  --output-csv final_result.csv --limit-cats 5 --source-csv filtered.csv

# 4. Translate: (Optional) Translate abstracts, titles, or labels
mlate translate --input final_result.csv --output final_en.csv --lang "English" \
  --cols "Title,Abstract,Application_category"
```

### 📝 CLI Reference (English)

| Command | Argument | Description |
| :--- | :--- | :--- |
| **Global** | `--model` | LLM model name (e.g., `deepseek-chat`, `gpt-4o`). |
| | `--source` | Data source format (`wos`, `scopus`, `standard`, `auto`). |
| **filter** | `--topic` | Topic keywords for relevance scoring. |
| | `--min-score` | Passing threshold (1-5, default 3.0). |
| | `--output-lang`| **(Multilingual)** Language for scoring criteria and reasons. |
| **explore** | `--dims` | Initial discovery dimensions (e.g., Application, Technology). |
| | `--guide` | Researcher guidance to fine-tune AI discovery. |
| | `--output-lang`| **(Multilingual)** Language for raw labels and reasons. |
| **converge** | `--limit-cats` | Max number of categories per dimension. |
| | `--dims` | **(Incremental)** Only process specified dimensions. |
| | `--output-csv` | **(Core)** Path to save the dual-labeled CSV file. |
| | `--source-csv` | Source CSV path for title mapping. |
| | `--output-lang`| **(Multilingual)** Language for category definitions. |
| **translate**| `--lang` | Target language for translation. |
| | `--cols` | **(CSV only)** Columns to translate (comma separated). |
| **config** | `set/show` | Manage global settings (model, language, etc.). |

---

### ⚠️ Disclaimer / 免责声明

- **AI Hallucinations**: All results (relevance scores, categories, reasons, and translations) are generated by Large Language Models (LLMs). LLMs are prone to **hallucinations** and may produce inaccurate, biased, or entirely fabricated information.
- **Manual Verification Required**: This tool is for **research assistance only**. Users must manually verify all AI-generated outputs before using them in academic publications or formal reports.
- **No Liability**: The author and MLATE contributors are not responsible for any research errors, data misinterpretations, or losses resulting from the use of this tool.

---

- **AI 幻觉风险**：本工具产出的所有结果（相关性评分、分类标签、理由、翻译等）均由大语言模型（LLM）生成。LLM 存在**幻觉（Hallucination）**可能，会产生不准确、有偏见甚至完全虚构的内容。
- **需人工核对**：本工具仅作为**研究辅助**。在将其产出内容用于学术论文、决策建议或正式报告前，研究者必须进行人工核对与审阅。
- **免责条款**：作者不对因使用本工具导致的任何研究偏差、数据解读错误或相关损失承担责任。

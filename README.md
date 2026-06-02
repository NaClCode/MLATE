# MLATE — Multi-dimensional Literature Analysis and Thematic Exploration
## 文献多维分析与主题探索工具

[English](#english) | [中文](#中文)

---

<a name="english"></a>
## 🇬🇧 English

MLATE is a high-precision literature analysis pipeline designed to transform raw bibliographic data (e.g., WoS, Scopus) into a structured, evidence-based taxonomic framework using LLMs.

### 🚀 Key Features
- **One-by-One Discovery**: Analyzes each paper independently to capture fine-grained details, eliminating "Batch-processing Bias."
- **Streaming Convergence**: A decoupled refinement phase that merges raw labels into a professional taxonomy using **Popularity-Aware** algorithms.
- **Incremental Refinement**: Supports refining specific dimensions (e.g., "Applications") multiple times without re-running the expensive discovery stage.
- **Dual-Category CSV Output**: Generates final reports with both `raw_category` (diverse) and `category` (refined/converged) for comparative analysis.
- **Auto Title Mapping**: Automatically replaces numeric IDs with real paper titles in the final JSON report.

### 🛠 Workflow
1. **`filter`**: Relevance scoring (1-5) and noise removal.
2. **`explore`**: Spontaneous discovery of raw labels for every paper.
3. **`converge`**: Intelligent merging, taxonomy refinement, and final labeling.

### 📖 Quick Start
```bash
# 1. Filter: Extract core papers (Relevance >= 3)
mlate filter --input raw_data.xls --topic "large language model" --output filtered.csv

# 2. Explore: Discover raw sub-categories (One-by-one mode)
# Output: raw_draft.json (Detailed but messy)
mlate explore --input filtered.csv --output raw_draft.json --dims "Application,Technology"

# 3. Converge: Incremental Refinement & Final Labeling
# Output: taxonomy.json (Professional report) & final_labeled.csv (Ready for analysis)
mlate converge --input raw_draft.json --output taxonomy.json \
  --output-csv final_labeled.csv --limit-cats 5 --source-csv filtered.csv \
  --guide "Focus on industrial automation scenarios."
```

---

<a name="中文"></a>
## 🇨🇳 中文

MLATE (Multi-dimensional Literature Analysis and Thematic Exploration) 是一个专注于**高精度、证据导向**的文献分析工具。它能将原始文献数据（如 Web of Science 导出的 Excel）深度解构，并自动构建出严谨的学术分类体系。

### 🌟 核心功能
- **逐篇深度探索 (Discovery)**：对每一篇文献进行独立问询，捕捉最细微的研究特征，彻底解决大批量处理时信息被模糊的问题。
- **智能流式收敛 (Convergence)**：探索与收敛阶段完全解耦。收敛过程会自动权衡“语义相似度”与“样本支撑数”，确保分类体系既有热度支撑又具备学术深度。
- **增量式迭代**：支持针对特定维度（如“应用场景”）反复调整收敛参数，系统会自动保护其他已完成的维度。
- **双分类标注体系**：最终生成的 CSV 报表同时包含 `原始标签` 与 `收敛大类`，方便研究者核对分类演化逻辑。
- **全量标题回填**：分类报告自动将原始 ID 映射回论文标题，直接产出可供发表使用的学术分析报告。

### 📖 快速上手
```bash
# 1. 主题筛选
mlate filter --input data.xls --topic "知识图谱在工业中的应用" --output filtered.csv

# 2. 第一阶段：逐篇探索 (产生原始多样化草案)
mlate explore --input filtered.csv --output draft.json --dims "应用场景,技术路径"

# 3. 第二阶段：智能收敛 (产出最终报告与带双列标签的 CSV)
# 您可以多次运行此命令，单独微调某个维度而不影响其他维度
mlate converge --input draft.json --output taxonomy.json \
  --output-csv final_result.csv \
  --dims "应用场景" \
  --limit-cats 5 --source-csv filtered.csv \
  --guide "请侧重识别工业故障诊断相关的子类。"
```

---

### 📝 命令行参数参考 (CLI Reference)

| 命令 | 参数 | 描述 |
| :--- | :--- | :--- |
| **filter** | `--min-score` | 设定通过阈值（默认 3.0）。 |
| **explore** | `--dims` | 设定探索的初始维度（如：应用场景,技术路径）。 |
| **converge** | `--limit-cats` | 每个维度最终保留的分类数量上限（收敛数）。 |
| | `--dims` | **(增量更新)** 本次只收敛特定的维度。 |
| | `--output-csv`| **(核心功能)** 生成带双列标签（Raw vs Refined）的最终文献库。 |
| | `--source-csv`| 原始 CSV 路径，用于将 ID 映射回论文标题。 |
| **config** | `set lang` | 切换日志语言 (cn/en/both)。 |

---

### 🔒 安全与配置
- **API Key**：出于安全考虑，系统**仅**支持通过环境变量（如 `MLATE_API_KEY`）获取 Key，禁止本地存储。
- **环境隔离**：配置文件（非敏感）存储在 `~/.mlate/config.json` 中。

# MLATE — Multi-dimensional Literature Analysis and Thematic Exploration

[English](README.md) | 中文版

---

MLATE (Multi-dimensional Literature Analysis and Thematic Exploration) 是一个辅助研究者进行文献解构与分类体系构建的命令行工具。它利用大语言模型（LLM）自动化处理文献数据，协助研究者从海量文献中梳理研究维度并生成初步的学术分类。

## 主要功能

- **逐篇文献探索**: 对每篇文献独立进行特征提取与初步分类，旨在捕捉细节，减少大批量处理时的信息丢失与偏见。
- **两阶段收敛逻辑**: 将"原始多样化发现"与"分类体系收敛"分阶段。收敛过程基于语义相似与样本热度进行标签合并。
- **增量式迭代调优**: 支持针对特定维度（如"应用场景"）反复调整收敛参数，系统会自动保护其他已处理维度的存量数据。
- **双分类标注体系**: 最终生成的 CSV 报表同时保留原始标签与收敛后的大类，方便研究者核对 AI 的分类演化逻辑。
- **自动化翻译支持**: 内置翻译模块，支持利用 LLM 对文献标题、摘要及分类结果进行多语言转换。

## 快速上手

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

## 命令行参数参考

| 命令 | 参数 | 描述 |
| :--- | :--- | :--- |
| **全局选项** | `--model` | 指定模型名（如 `deepseek-chat`, `gpt-4o`）。 |
| | `--source` | 数据源格式 (`wos`, `scopus`, `standard`, `auto`)。 |
| **filter** | `--topic` | 用于相关性评分的主题关键词。 |
| | `--min-score` | 筛选阈值（1-5，默认 3.0）。分数越高筛选越严。 |
| | `--output-lang`| 评分标准与理由的生成语言。 |
| **explore** | `--dims` | 初始探索维度（如：应用场景,技术路径）。 |
| | `--guide` | 研究者引导词，用于精细化控制 AI 探索方向。 |
| | `--output-lang`| 原始标签与理由的生成语言。 |
| **converge** | `--limit-cats` | 每个维度最终保留的分类数量上限。 |
| | `--dims` | 仅对指定的维度进行收敛处理（增量更新）。 |
| | `--output-csv` | 生成带原始标签与收敛大类的标注文献库。 |
| | `--source-csv` | 原始 CSV 路径，用于将 ID 映射回论文标题。 |
| | `--output-lang`| 分类定义与判定标准的生成语言。 |
| **translate**| `--lang` | 目标翻译语言（如 English, 中文）。 |
| | `--cols` | 指定需要翻译的列名（逗号分隔，CSV专用）。 |
| **config** | `set/show` | 管理全局配置（如默认模型、输出语言、日志级别）。 |

## 配置说明

- **API Key**：通过环境变量 `MLATE_API_KEY` 设置，为安全考虑不落盘存储。
- **全局语言配置**：
  ```bash
  mlate config set output_lang English
  ```

## 免责声明

本工具产出的所有结果（相关性评分、分类标签、理由、翻译等）均由大语言模型（LLM）生成。LLM 存在幻觉（Hallucination）可能，会产生不准确、有偏见甚至完全虚构的内容。本工具仅作为研究辅助，在将其产出内容用于学术论文、决策建议或正式报告前，研究者必须进行人工核对与审阅。作者不对因使用本工具导致的任何研究偏差、数据解读错误或相关损失承担责任。

"""MLATEPipeline — 编排器：加载 prompt 模板 → 委托各 stage

提示词统一存放在 prompts/*.md，使用 {{variable}} 模板语法注入。
"""
import json, random
import pandas as pd
from pathlib import Path

from tqdm import tqdm
from llm import LLM, RateLimiter
from stages import filter_stage, explore_stage, classify_stage
from logger import logger
from loaders import BaseLoader
from utils import render_prompt, safe_str

_HERE = Path(__file__).parent
_DEFAULT_PROMPT_DIR = _HERE / "prompts"


def load_prompt(name: str, prompt_dir: str = None) -> str:
    """从 markdown 文件加载 prompt 模板"""
    d = Path(prompt_dir) if prompt_dir else _DEFAULT_PROMPT_DIR
    path = d / name
    if not path.suffix:
        path = path.with_suffix(".md")
    return path.read_text(encoding="utf-8")


def _show_samples(df, label="结果", mapping=None):
    # If filter stage, only show passed ones
    target_df = df
    if "passed" in df.columns:
        target_df = df[df["passed"] == True]
        
    n = min(5, len(target_df))
    if n == 0:
        return
    
    samples = target_df.sample(n=n, random_state=random.randint(0, 99999))
    logger.section(f"{label}随机抽查 {n} 篇", f"Random check {n} papers from {label}")
    
    # Identify title column
    title_col = mapping.get("title") if mapping else "Title"
    if title_col not in df.columns:
        # Fallback to any common name
        for c in ["Title", "TI", "Article Title"]:
            if c in df.columns:
                title_col = c
                break

    for i, (_, row) in enumerate(samples.iterrows(), 1):
        raw_title = row.get(title_col, "")
        title = safe_str(raw_title)[:80]
        score = row.get("score")
        score_str = f"(评分={score}) " if score is not None and not (isinstance(score, float) and pd.isna(score)) else ""
        logger.info(f"  [{i}] {score_str}{title}…")


def _show_data_peek(df, mapping):
    """在运行初期展示 5 个样本，确认列提取是否正确"""
    n = min(5, len(df))
    if n == 0:
        return
    
    samples = df.head(n)
    logger.section(f"数据预览 (前 {n} 篇)", f"Data Peek (First {n} papers)")
    
    t_col = mapping.get("title")
    a_col = mapping.get("abstract")
    k_col = mapping.get("keywords")
    
    for i, (_, row) in enumerate(samples.iterrows(), 1):
        title = safe_str(row.get(t_col, ""))[:80]
        # Peek at abstract and keywords
        abstract = safe_str(row.get(a_col, ""))[:100]
        keywords = safe_str(row.get(k_col, ""))
        
        logger.info(f"  [{i}] Title: {title}…")
        logger.info(f"      Abs  : {abstract}…")
        logger.info(f"      Key  : {keywords}")
        logger.info("-" * 40)


class MLATEPipeline:
    def __init__(
        self,
        model: str = None, api_base: str = None,
        prompt_dir: str = None,
        max_workers: int = 8, qps: float = 2.0,
    ):
        self.llm = LLM(model, api_base)
        self.max_workers = max_workers
        self.qps = qps
        self.limiter = RateLimiter(qps)
        self.prompt_dir = prompt_dir or str(_DEFAULT_PROMPT_DIR)

    # ── filter ──
    def filter(self, input_csv: str, output_csv: str = None,
               topic: str = "", min_score: float = 3.0,
               source_type: str = "auto", language: str = "中文") -> "pd.DataFrame":
        df, mapping = BaseLoader.load(input_csv, source_type)
        _show_data_peek(df, mapping)
        
        prompt_criteria = load_prompt("filter_criteria", self.prompt_dir)
        prompt_score = load_prompt("filter_score", self.prompt_dir)

        full_out = filter_stage.run_filter(
            df, topic, min_score, self.llm, self.limiter, self.max_workers,
            mapping["title"], mapping["abstract"], mapping["keywords"],
            prompt_criteria, prompt_score,
            output_lang=language
        )
        _show_samples(full_out, "筛选后", mapping=mapping)
        
        if output_csv:
            # 1. Save filtered (only passed)
            filtered_df = full_out[full_out["passed"] == True]
            filtered_df.to_csv(output_csv, index=False, encoding="utf-8-sig")
            logger.success(f"已保存筛选后文献: {output_csv}", f"Saved filtered papers: {output_csv}")
            
            # 2. Save all (full data)
            path = Path(output_csv)
            all_path = path.with_name(f"{path.stem}_all{path.suffix}")
            full_out.to_csv(all_path, index=False, encoding="utf-8-sig")
            logger.info(f"已保存全量评分数据: {all_path}", f"Saved all scoring data: {all_path}")
            
        return full_out

    # ── explore ──
    def explore(self, input_csv: str, output_raw_json: str,
                max_papers: int = None,
                source_type: str = "auto", researcher_guide: str = None,
                initial_dims: str = None, language: str = "中文") -> dict:
        """Phase 1: Spontaneous Discovery of sub-categories (Per-paper)"""
        df, mapping = BaseLoader.load(input_csv, source_type)
        _show_data_peek(df, mapping)
        
        if max_papers and max_papers < len(df):
            df = df.iloc[:max_papers]

        prompt_explore = load_prompt("explore", self.prompt_dir)
        raw_accum = explore_stage.run_explore(
            df, initial_dims, prompt_explore, self.llm, self.limiter,
            self.max_workers,
            mapping["title"], mapping["abstract"], mapping["keywords"],
            researcher_guide=researcher_guide,
            output_lang=language
        )

        with open(output_raw_json, "w", encoding="utf-8") as f:
            json.dump(raw_accum, f, ensure_ascii=False, indent=2)
        logger.success(f"原始探索草案已保存: {output_raw_json}", f"Raw discovery draft saved: {output_raw_json}")
        return raw_accum

    # ── converge ──
    def converge(self, input_raw_json: str, output_taxonomy: str,
                 limit_cats: int = 10, target_dims: str = None,
                 researcher_guide: str = None, source_csv: str = None,
                 output_csv: str = None, language: str = "中文") -> dict:
        """Phase 2: Intelligent Convergence and Auto-Labeling (Supports Incremental Update)"""
        with open(input_raw_json, encoding="utf-8") as f:
            all_raw_accum = json.load(f)

        # 1. Determine dimensions to process
        available_dims = list(all_raw_accum.keys())
        if not target_dims:
            logger.info(f"未指定维度，将处理所有发现的维度: {', '.join(available_dims)}",
                        f"No dims specified, processing all: {', '.join(available_dims)}")
            requested_dims = available_dims
        else:
            requested_dims = [d.strip() for d in target_dims.split(",") if d.strip()]
            # Validate
            requested_dims = [d for d in requested_dims if d in available_dims]
            if not requested_dims:
                logger.error(f"指定的维度不存在。可用维度: {', '.join(available_dims)}",
                             f"None of the specified dims exist. Available: {', '.join(available_dims)}")
                return {}
            logger.info(f"本次收敛维度: {', '.join(requested_dims)}", 
                        f"Converging selected dims: {', '.join(requested_dims)}")

        raw_accum_to_process = {k: all_raw_accum[k] for k in requested_dims}

        # 2. Prepare Source Data
        id_to_title = None
        df = None
        if source_csv:
            df, mapping = BaseLoader.load(source_csv, "auto")
            id_to_title = {i + 1: safe_str(row[mapping["title"]]) for i, row in df.iterrows()}

        # 3. Perform Convergence
        prompt_converge = load_prompt("converge", self.prompt_dir)
        new_taxonomy, mapping_table = explore_stage.run_converge(
            raw_accum_to_process, limit_cats, prompt_converge, self.llm, self.limiter,
            researcher_guide=researcher_guide,
            id_to_title=id_to_title,
            output_lang=language
        )

        # 4. Incremental JSON Update
        final_tax = {}
        if Path(output_taxonomy).exists():
            try:
                with open(output_taxonomy, encoding="utf-8") as f:
                    final_tax = json.load(f)
            except: pass
        
        # Merge new into old (overwrite selected dims)
        for dim, content in new_taxonomy.items():
            final_tax[dim] = content

        with open(output_taxonomy, "w", encoding="utf-8") as f:
            json.dump(final_tax, f, ensure_ascii=False, indent=2)
        logger.success(f"分类体系已更新并保存: {output_taxonomy}", f"Taxonomy updated and saved: {output_taxonomy}")

        # 5. Incremental CSV Update (Auto-Labeling)
        if output_csv:
            # If output_csv exists, we update it; otherwise we use the source_csv as base
            target_df = None
            if Path(output_csv).exists():
                target_df = pd.read_csv(output_csv, encoding="utf-8-sig")
            elif df is not None:
                target_df = df.copy()

            if target_df is not None:
                paper_labels = {} # { paper_id -> { dim -> (final_cat, reason, raw_cat) } }
                for dim in requested_dims:
                    m_table = mapping_table.get(dim, {})
                    for item in all_raw_accum[dim]:
                        pid = item["paper_id"]
                        raw_cat = item["category"]
                        # 确保映射到最终收敛类，找不到则记录原始
                        final_cat = m_table.get(raw_cat, raw_cat)
                        paper_labels.setdefault(pid, {})
                        paper_labels[pid][dim] = (final_cat, item["reason"], raw_cat)

                # Update columns
                for dim in requested_dims:
                    target_df[f"{dim}_raw_category"] = target_df.get(f"{dim}_raw_category", "")
                    target_df[f"{dim}_category"] = target_df.get(f"{dim}_category", "")
                    target_df[f"{dim}_reason"] = target_df.get(f"{dim}_reason", "")
                    
                for idx, row in target_df.iterrows():
                    pid = idx + 1
                    if pid in paper_labels:
                        for dim, (f_cat, reason, r_cat) in paper_labels[pid].items():
                            target_df.at[idx, f"{dim}_raw_category"] = r_cat
                            target_df.at[idx, f"{dim}_category"] = f_cat
                            target_df.at[idx, f"{dim}_reason"] = reason

                target_df.to_csv(output_csv, index=False, encoding="utf-8-sig")
                logger.success(f"文献标注已增量更新: {output_csv}", f"CSV labels updated incrementally: {output_csv}")

        return final_tax

    # ── translate ──
    def translate(self, input_file: str, output_file: str, target_lang: str = "中文", columns: str = None) -> None:
        """Translate CSV columns or JSON text values using LLM"""
        logger.info(f"正在翻译 {input_file} -> {target_lang}...", f"Translating {input_file} to {target_lang}...")
        
        ext = Path(input_file).suffix.lower()
        
        if ext == ".csv":
            df = pd.read_csv(input_file)
            if not columns:
                logger.error("CSV 翻译需要指定 --cols 参数", "CSV translation requires --cols parameter")
                return
            
            cols_to_translate = [c.strip() for c in columns.split(",") if c.strip()]
            for col in cols_to_translate:
                if col not in df.columns:
                    logger.warning(f"列 {col} 不存在，跳过", f"Column {col} not found, skipping")
                    continue
                
                logger.info(f"  正在翻译列: {col}...", f"  Translating column: {col}...")
                unique_texts = df[col].dropna().unique()
                
                # Batch translate unique texts to save tokens
                text_map = {}
                # Determine batch size based on text length
                avg_len = sum(len(str(t)) for t in unique_texts[:10]) / 10 if len(unique_texts) > 0 else 0
                batch_size = 1 if avg_len > 500 else (5 if avg_len > 100 else 20)
                
                logger.info(f"    检测到平均长度 {int(avg_len)}，采用 BatchSize={batch_size}", 
                            f"    Avg length {int(avg_len)}, using BatchSize={batch_size}")

                for i in tqdm(range(0, len(unique_texts), batch_size)):
                    batch = unique_texts[i:i+batch_size]
                    if batch_size == 1:
                        # Single long text (like abstract)
                        prompt = f"请将以下学术文本翻译成{target_lang}，保持专业术语准确，直接返回翻译后的文本：\n\n{batch[0]}"
                        self.limiter.wait()
                        res_text = self.llm.chat([{"role": "user", "content": prompt}])
                        if res_text:
                            text_map[batch[0]] = res_text
                    else:
                        # Multiple short texts (like categories or titles)
                        prompt = f"请将以下文本列表翻译成{target_lang}，保持专业术语准确，返回 JSON 对象 {{'original': 'translation'}}:\n\n" + json.dumps(list(batch), ensure_ascii=False)
                        self.limiter.wait()
                        res = self.llm.chat_json([{"role": "user", "content": prompt}])
                        if res:
                            text_map.update(res)
                
                df[col] = df[col].map(lambda x: text_map.get(x, x))
            
            df.to_csv(output_file, index=False, encoding="utf-8-sig")
            
        elif ext == ".json":
            with open(input_file, encoding="utf-8") as f:
                data = json.load(f)
            
            # Recursive translation for JSON values (simple implementation)
            def translate_value(val):
                if isinstance(val, str) and len(val) > 1:
                    prompt = f"请将以下学术短语或段落翻译成{target_lang}，直接返回翻译后的文本：\n\n{val}"
                    self.limiter.wait()
                    return self.llm.chat([{"role": "user", "content": prompt}])
                elif isinstance(val, list):
                    return [translate_value(v) for v in val]
                elif isinstance(val, dict):
                    return {k: translate_value(v) for k, v in val.items()}
                return val

            # For JSON, we might want to be more selective, but for now translate everything
            translated_data = translate_value(data)
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(translated_data, f, ensure_ascii=False, indent=2)
        
        logger.success(f"翻译完成: {output_file}", f"Translation completed: {output_file}")

    # ── classify ──
    def classify(self, input_csv: str, output_csv: str,
                 schema: str, classify_mode: str = "single",
                 source_type: str = "auto", researcher_guide: str = None,
                 language: str = "中文") -> pd.DataFrame:
        """Classify papers into user-defined categories (single-label or multi-label)"""
        df, mapping = BaseLoader.load(input_csv, source_type)
        total = len(df)
        logger.info(f"加载文献: {total} 篇", f"Loaded {total} papers")

        # 解析分类体系
        schema_path = Path(schema)
        if schema_path.exists():
            # 从文件读取
            raw = schema_path.read_text(encoding="utf-8")
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError:
                parsed = [line.strip() for line in raw.split("\n") if line.strip()]
        else:
            # 以逗号分隔的 inline 分类
            parsed = [c.strip() for c in schema.split(",") if c.strip()]

        prompt_classify = load_prompt("classify", self.prompt_dir)
        result_df = classify_stage.run_classify(
            df, parsed, classify_mode, prompt_classify, self.llm, self.limiter,
            self.max_workers,
            mapping["title"], mapping["abstract"], mapping["keywords"],
            researcher_guide=researcher_guide,
            output_lang=language
        )

        result_df.to_csv(output_csv, index=False, encoding="utf-8-sig")
        logger.success(f"分类结果已保存: {output_csv}", f"Classification results saved: {output_csv}")
        return result_df

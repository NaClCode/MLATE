"""MLATEPipeline — 编排器：加载 prompt 模板 → 委托各 stage

提示词统一存放在 prompts/*.md，使用 {{variable}} 模板语法注入。
"""
import json, random
import pandas as pd
from pathlib import Path
from llm import LLM, RateLimiter
from stages import filter_stage, explore_stage, analyze_stage
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


def _infer_dimensions(tax: dict) -> list:
    return [{"name": k, "prefix": k[:4], "desc": "", "categories": list(v.keys())}
            for k, v in tax.items()]


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
               source_type: str = "auto") -> "pd.DataFrame":
        df, mapping = BaseLoader.load(input_csv, source_type)
        _show_data_peek(df, mapping)
        
        prompt_criteria = load_prompt("filter_criteria", self.prompt_dir)
        prompt_score = load_prompt("filter_score", self.prompt_dir)

        full_out = filter_stage.run_filter(
            df, topic, min_score, self.llm, self.limiter, self.max_workers,
            mapping["title"], mapping["abstract"], mapping["keywords"],
            prompt_criteria, prompt_score,
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
    def explore(self, input_csv: str, output_taxonomy: str,
                batch_size: int = 20, max_papers: int = None,
                source_type: str = "auto", researcher_guide: str = None) -> dict:
        df, mapping = BaseLoader.load(input_csv, source_type)
        _show_data_peek(df, mapping)
        
        if max_papers and max_papers < len(df):
            df = df.iloc[:max_papers]

        dims = [] # Always start with empty dims for exploration
        prompt = load_prompt("explore", self.prompt_dir)

        full_accum = explore_stage.run_explore(
            df, dims, prompt, self.llm, self.limiter,
            batch_size, self.max_workers,
            mapping["title"], mapping["abstract"], mapping["keywords"],
            researcher_guide=researcher_guide,
        )
        with open(output_taxonomy, "w", encoding="utf-8") as f:
            json.dump(full_accum, f, ensure_ascii=False, indent=2)
        logger.info(f"→ {output_taxonomy}")
        return full_accum

    # ── analyze ──
    def analyze(self, input_csv: str, output_csv: str,
                taxonomy_file: str = None, max_papers: int = None,
                source_type: str = "auto") -> "pd.DataFrame":
        df, mapping = BaseLoader.load(input_csv, source_type)
        _show_data_peek(df, mapping)
        
        if max_papers and max_papers < len(df):
            df = df.iloc[:max_papers].copy()

        tax = {}
        if taxonomy_file:
            with open(taxonomy_file, encoding="utf-8") as f:
                tax = json.load(f)

        dims = _infer_dimensions(tax)
        prompt = load_prompt("analyze", self.prompt_dir)

        df = analyze_stage.run_analyze(
            df, dims, tax, prompt, self.llm, self.limiter,
            self.max_workers, mapping["title"], mapping["abstract"], mapping["keywords"],
        )
        _show_samples(df, "分析后", mapping=mapping)
        df.to_csv(output_csv, index=False, encoding="utf-8-sig")
        logger.info(f"→ {output_csv}")
        return df

    # ── retry ──
    def retry(self, csv_path: str, output_csv: str = None) -> int:
        # For retry, we assume it's a CSV and try to auto-identify columns
        df = pd.read_csv(csv_path, encoding="utf-8-sig")
        df, mapping = BaseLoader.identify_columns(df, "auto")
        
        dc = [c for c in df.columns if c.endswith("_category")]
        dims = [{"name": c.replace("_category", ""), "prefix": c.replace("_category", "")[:4]} for c in dc]
        
        tax = {} # Placeholder
        prompt = load_prompt("analyze", self.prompt_dir)

        df = analyze_stage.retry_errors(
            df, dims, tax, prompt, self.llm, self.limiter,
            self.max_workers, mapping["title"], mapping["abstract"], mapping["keywords"],
        )
        out = output_csv or csv_path
        df.to_csv(out, index=False, encoding="utf-8-sig")
        dc = [c for c in df.columns if c.endswith("_category")]
        rem = (df[dc[0]] == "ERROR").sum() if dc else 0
        logger.info(f"剩余 ERROR: {rem}", f"Remaining ERROR: {rem}")
        return rem

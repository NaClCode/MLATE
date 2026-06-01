"""pandas 工具函数"""
import pandas as pd

__all__ = ["safe_str", "build_paper", "render_prompt"]


def safe_str(x) -> str:
    if x is None:
        return ""
    
    # Handle pandas Series (happens with duplicate column names)
    if isinstance(x, pd.Series):
        if x.empty:
            return ""
       
        valid_vals = [str(v).strip() for v in x.dropna() if str(v).strip()]
        if not valid_vals:
            return ""
        x = max(valid_vals, key=len)

    try:
        if isinstance(x, float) and pd.isna(x):
            return ""
    except Exception:
        pass
    return str(x).strip()


def build_paper(row: pd.Series, title_col="Title", abstract_col="Abstract", keywords_col="Keywords") -> str:
    """从原始行构建 LLM 所需的文本描述"""
    title = row.get(title_col, "")
    abstract = row.get(abstract_col, "")
    keywords = row.get(keywords_col, "")
    
    # Heuristic for keywords if empty
    if not safe_str(keywords):
        for c in ["Author Keywords", "Keywords Plus", "DE", "ID", "关键词"]:
            if c in row.index and safe_str(row[c]):
                keywords = row[c]
                break
        
    return (
        f"Title: {safe_str(title)}\n"
        f"Abstract: {safe_str(abstract)}\n"
        f"Keywords: {safe_str(keywords)}"
    )


def render_prompt(template: str, **kwargs) -> str:
    """渲染 prompt 模板，替换 {{variable}} 为具体值"""
    res = template
    for k, v in kwargs.items():
        res = res.replace("{{" + k + "}}", str(v))
    return res

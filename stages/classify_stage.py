"""分类阶段：根据用户预定义的分类体系，对文献进行自动归类

支持两种模式：
  - single: 每篇文献只归入一个最贴切的类别
  - multi: 每篇文献可归入零个或多个类别
"""
import json, threading
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
from ..utils import build_paper, render_prompt, safe_str
from ..logger import logger


def run_classify(df, schema, classify_mode, prompt_tpl, llm, limiter,
                 max_workers, title_col, abstract_col, keywords_col,
                 researcher_guide: str = None, output_lang: str = "中文"):
    """逐篇分类文献

    Args:
        df: 文献 DataFrame
        schema: 分类体系 (list of str) 或 JSON 格式的分类定义
        classify_mode: "single" 或 "multi"
        prompt_tpl: 提示词模板
        llm: LLM 实例
        limiter: 速率限制器
        max_workers: 最大并发数
        title_col: 标题列名
        abstract_col: 摘要列名
        keywords_col: 关键词列名
        researcher_guide: 研究者引导词
        output_lang: 输出语言

    Returns:
        pd.DataFrame: 添加了分类信息的 DataFrame
    """
    total = len(df)
    mode_cn = "单标签" if classify_mode == "single" else "多标签"
    mode_en = "Single-label" if classify_mode == "single" else "Multi-label"
    logger.info(f"自动分类: {total} 篇 ({mode_cn}模式)", 
                f"Auto-classifying: {total} papers ({mode_en} mode)")

    # 构建分类体系文本
    if isinstance(schema, list):
        schema_text = "\n".join(f"- {c}" for c in schema)
    elif isinstance(schema, dict):
        schema_text = json.dumps(schema, ensure_ascii=False, indent=2)
    else:
        schema_text = str(schema)

    logger.info(f"分类体系 ({len(schema) if isinstance(schema, list) else '?'} 个类别):\n{schema_text}",
                f"Classification schema ({len(schema) if isinstance(schema, list) else '?'} categories):\n{schema_text}")

    guide_text = researcher_guide if researcher_guide else "无特定引导。"

    results = {}
    lock = threading.Lock()
    pbar = tqdm(total=total, desc="Classifying", unit="paper")

    def worker(idx):
        paper_id = idx + 1
        row = df.iloc[idx]
        pt = build_paper(row, title_col, abstract_col, keywords_col)

        limiter.wait()
        result = llm.chat_json([{"role": "user", "content": render_prompt(prompt_tpl,
            schema_text=schema_text,
            classify_mode=classify_mode,
            paper_id=paper_id,
            paper_text=pt,
            researcher_guide=guide_text,
            output_lang=output_lang
        )}])
        return paper_id, result

    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = {ex.submit(worker, i): i for i in range(total)}

        for fut in as_completed(futures):
            paper_id, result = fut.result()
            with lock:
                results[paper_id] = result
            pbar.update(1)
    pbar.close()

    # 统计成功数
    success = sum(1 for v in results.values() if v)
    logger.info(f"分类完成: {success}/{total} 篇成功",
                f"Classification done: {success}/{total} papers succeeded")

    # 写入 DataFrame
    categories = []
    reasons = []
    keywords_list = []

    for idx in range(total):
        paper_id = idx + 1
        r = results.get(paper_id)

        if r:
            cat = r.get("category", "")
            reason = r.get("reason", "")
            kw = r.get("keywords", [])

            if classify_mode == "multi":
                # multi 模式下 category 是数组
                if isinstance(cat, list):
                    cat_str = "; ".join(cat)
                else:
                    cat_str = str(cat) if cat else ""
            else:
                cat_str = str(cat) if cat else ""

            categories.append(cat_str)
            reasons.append(reason)
            keywords_list.append("; ".join(kw) if isinstance(kw, list) else str(kw))
        else:
            categories.append("")
            reasons.append("")
            keywords_list.append("")

    df[f"classify_category"] = categories
    df[f"classify_reason"] = reasons
    df[f"classify_keywords"] = keywords_list

    # 统计分类分布
    from collections import Counter
    all_cats = []
    for c in categories:
        for cat in c.split("; "):
            if cat:
                all_cats.append(cat)
    cat_counter = Counter(all_cats)
    logger.section("分类分布", "Category Distribution")
    for cat, cnt in cat_counter.most_common():
        logger.info(f"  {cat}: {cnt}")

    return df

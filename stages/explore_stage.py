"""主题探索阶段：按批次发现大类内部的细分子类"""
import json
import pandas as pd
from tqdm import tqdm
from utils import build_paper, render_prompt, safe_str
from logger import logger


def run_explore(df, dims, prompt_tpl, llm, limiter,
                batch_size, max_workers, title_col, abstract_col, keywords_col,
                researcher_guide: str = None):
    total = len(df)
    logger.info(f"探索论文数: {total}", f"Exploring {total} papers")

    if dims:
        dims_desc = "目前我们已经定义了以下核心维度及初步分类：\n" + "\n".join(
            f"- {d['name']}: {', '.join(d.get('categories', []))}" for d in dims
        )
    else:
        dims_desc = "尚未定义维度。请根据数据内容自主发现最具学术价值的分析维度。"

    guide_text = researcher_guide if researcher_guide else "无特定引导，请基于文献内容自主探索。"

    full_accum = {}
    total_batches = (total + batch_size - 1) // batch_size

    pbar = tqdm(total=total_batches, desc="Exploring", unit="batch")
    for batch_num in range(total_batches):
        start, end = batch_num * batch_size, min((batch_num + 1) * batch_size, total)
        batch = df.iloc[start:end]
        # logger.info(f"批次 {batch_num+1}/{total_batches}", f"Batch {batch_num+1}/{total_batches}")

        # Prepare batch text
        papers_lines = []
        for i in range(len(batch)):
            paper_id = start + i + 1
            papers_lines.append(f"#{paper_id} {build_paper(batch.iloc[i], title_col, abstract_col, keywords_col)}")

        papers_text = "\n".join(papers_lines)
        limiter.wait()
        result = llm.chat_json([{"role": "user", "content": render_prompt(prompt_tpl,
            dimensions_desc=dims_desc, batch_num=batch_num + 1, papers_text=papers_text,
            researcher_guide=guide_text,
        )}])
        if not result:
            pbar.update(1)
            continue

        refine = result.get("细化建议", {})
        for dim_key, dim_data in refine.items():
            full_accum.setdefault(dim_key, {})
            for parent_cat, subcats in dim_data.items():
                full_accum[dim_key].setdefault(parent_cat, [])
                for sc in subcats:
                    name = sc.get("细分子类", "").strip()
                    if not name:
                        continue
                    
                    existing = {s["name"] for s in full_accum[dim_key][parent_cat]}
                    if name not in existing:
                        full_accum[dim_key][parent_cat].append({
                            "name": name,
                            "definition": sc.get("定义", ""),
                            "keywords": sc.get("关键词", ""),
                            "typical_cases": sc.get("典型案例", [])[:3],
                            "judgment_suggestions": sc.get("判定建议", ""),
                        })

        for dk, dd in refine.items():
            for pc, scs in dd.items():
                names = [s["细分子类"] for s in scs if s.get("细分子类")]
                if names:
                    logger.info(f"  {dk} > {pc}: {', '.join(names)}")
        
        pbar.update(1)

    pbar.close()
    return full_accum

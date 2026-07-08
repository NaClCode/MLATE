"""主题探索阶段：逐篇发现草案 + 智能收敛"""
import json, threading
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
from ..utils import build_paper, render_prompt, safe_str
from ..logger import logger


def run_explore(df, dims, prompt_tpl, llm, limiter,
                max_workers, title_col, abstract_col, keywords_col,
                researcher_guide: str = None, output_lang: str = "中文"):
    total = len(df)
    logger.info(f"深度探索论文数: {total} (逐篇处理)", f"Exploring {total} papers (one-by-one)")

    if dims:
        dims_list = [d.strip() for d in dims.split(",") if d.strip()]
        dims_desc = "目前研究者已经设定了以下核心维度：\n" + "\n".join(f"- {d}" for d in dims_list)
    else:
        dims_desc = "尚未定义维度。请根据数据内容自主发现最具学术价值的分析维度。"

    guide_text = researcher_guide if researcher_guide else "无特定引导，请基于文献内容自主探索。"

    full_accum = {}
    lock = threading.Lock()

    def worker(idx):
        paper_id = idx + 1
        row = df.iloc[idx]
        pt = build_paper(row, title_col, abstract_col, keywords_col)
        
        limiter.wait()
        result = llm.chat_json([{"role": "user", "content": render_prompt(prompt_tpl,
            dimensions_desc=dims_desc, paper_id=paper_id, paper_text=pt,
            researcher_guide=guide_text, output_lang=output_lang
        )}])
        return result

    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        pbar = tqdm(total=total, desc="Exploring (Phase 1: Individual Discovery)", unit="paper")
        futures = {ex.submit(worker, i): i for i in range(total)}
        
        for fut in as_completed(futures):
            result = fut.result()
            paper_id = futures[fut] + 1
            if result:
                with lock:
                    for dim_key, data in result.items():
                        full_accum.setdefault(dim_key, [])
                        if isinstance(data, dict):
                            full_accum[dim_key].append({
                                "paper_id": paper_id,
                                "category": data.get("category", ""),
                                "reason": data.get("reason", "")
                            })
            
            pbar.update(1)
        pbar.close()

    return full_accum


def run_converge(raw_taxonomy, limit_cats, prompt_tpl, llm, limiter, researcher_guide=None, id_to_title=None, output_lang="中文"):
    """Phase 2: Iterative Taxonomy Convergence & Popularity-based Merging"""
    logger.section(f"第二阶段：智能收敛 (目标每维度 {limit_cats} 类)...", 
                   f"Phase 2: Intelligent Convergence (Target {limit_cats} cats/dim)...")
    
    final_taxonomy = {}
    # mapping_table: { dimension -> { raw_label -> final_label } }
    mapping_table = {}

    for dim, raw_items in raw_taxonomy.items():
        logger.info(f"正在处理维度: {dim} (共 {len(raw_items)} 条原始标签)", 
                    f"Processing dimension: {dim} ({len(raw_items)} raw labels)")
        
        # 1. 统计原始标签频率
        from collections import Counter
        counts = Counter(item["category"] for item in raw_items)
        unique_labels = sorted(counts.items(), key=lambda x: -x[1]) # 按热度排序
        
        # 2. 迭代收敛：分块处理以防止 Context 溢出并实现流式合并
        chunk_size = 30 
        current_refined_cats = [] # 存储当前收敛后的 [{name, definition, ...}]
        
        label_to_final = {} # 记录原始标签到最终标签的映射

        for i in range(0, len(unique_labels), chunk_size):
            chunk = unique_labels[i:i+chunk_size]
            chunk_text = "\n".join([f"- {name} (样本数: {count})" for name, count in chunk])
            existing_text = json.dumps(current_refined_cats, ensure_ascii=False) if current_refined_cats else "None"
            
            limiter.wait()
            res = llm.chat_json([{"role": "user", "content": render_prompt(prompt_tpl,
                dim_name=dim,
                new_labels=chunk_text,
                existing_taxonomy=existing_text,
                limit_cats=limit_cats,
                researcher_guide=researcher_guide or "无特定引导。",
                output_lang=output_lang
            )}])
            
            if res:
                current_refined_cats = res.get("refined_categories", [])
                new_mappings = res.get("mapping", {}) # {"原始/中间标签": "新标签"}
                
                # ── 关键：级联映射更新 (Transitive Mapping) ──
                # 1. 更新已有的映射路径：如果 A->B, 现在 B->C，则更新为 A->C
                for raw_label, current_final in label_to_final.items():
                    if current_final in new_mappings:
                        label_to_final[raw_label] = new_mappings[current_final]
                
                # 2. 存入本批次的新映射
                label_to_final.update(new_mappings)

        # 3. 最终热度裁剪与标题映射
        # 确保不超过 limit_cats，并回填标题
        final_taxonomy[dim] = {"Default": current_refined_cats[:limit_cats]}
        mapping_table[dim] = label_to_final

    # ── 标题回填 ──
    if id_to_title:
        for dim, categories in final_taxonomy.items():
            for cat_group, subcats in categories.items():
                for sc in subcats:
                    sc_name = sc["name"]
                    # 找到所有映射到这个 final_category 的原始论文
                    mapped_raw_labels = [raw for raw, fin in mapping_table[dim].items() if fin == sc_name]
                    
                    cases = []
                    for item in raw_taxonomy[dim]:
                        if item["category"] in mapped_raw_labels:
                            title = id_to_title.get(item["paper_id"], f"ID:{item['paper_id']}")
                            cases.append(f"《{title}》: {item['reason']}")
                    
                    sc["typical_cases"] = cases[:5] # 保留前5个典型案例

    return final_taxonomy, mapping_table

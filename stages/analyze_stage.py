"""维度分析阶段：逐篇两级分类标注"""
import threading
import pandas as pd
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import Counter
from utils import build_paper, render_prompt
from logger import logger


def run_analyze(df, dims, tax, prompt_tpl, llm, limiter,
                max_workers, title_col, abstract_col, keywords_col):
    total = len(df)
    logger.info(f"分析论文数: {total}", f"Analyzing {total} papers")

    dims_desc = _build_dims_desc(dims, tax)
    ext_fields = ["is_review", "review_evidence"]
    for dim in dims:
        p = dim.get("prefix", dim["name"][:4])
        ext_fields += [f"{p}_category", f"{p}_subcategory",
                       f"{p}_evidence", f"{p}_sub_evidence", f"{p}_reason"]
    for c in ext_fields:
        df[c] = ""

    lock = threading.Lock()

    def worker(idx, row):
        pt = build_paper(row, title_col, abstract_col, keywords_col)
        limiter.wait()
        result = llm.chat_json([{"role": "user", "content": render_prompt(prompt_tpl,
            dimensions_desc=dims_desc, paper_text=pt,
        )}])
        if not result:
            return idx, {c: "ERROR" for c in ext_fields}
        data = {
            "is_review": result.get("是否综述性论文", ""),
            "review_evidence": result.get("综述判断依据", ""),
        }
        for dim in dims:
            p = dim.get("prefix", dim["name"][:4])
            d = result.get(dim["name"], {})
            data.update({f"{p}_category": d.get("大类", ""),
                         f"{p}_subcategory": d.get("子类", ""),
                         f"{p}_evidence": d.get("依据", ""),
                         f"{p}_sub_evidence": d.get("细化依据", ""),
                         f"{p}_reason": d.get("理由", "")})
        return idx, data

    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        pbar = tqdm(total=total, desc="Analyzing", unit="paper")
        fs = {ex.submit(worker, i, df.iloc[i]): i for i in range(total)}
        for fut in as_completed(fs):
            idx, data = fut.result()
            with lock:
                for c, v in data.items():
                    df.at[idx, c] = v
            pbar.update(1)
        pbar.close()

    for dim in dims:
        p = dim.get("prefix", dim["name"][:4])
        col = f"{p}_category"
        cnt = Counter(str(v) for v in df[col] if str(v) not in ("", "ERROR"))
        logger.section(f"{dim['name']} ({sum(cnt.values())})")
        for k, v in sorted(cnt.items(), key=lambda x: -x[1]):
            logger.info(f"  {k}: {v}")

    return df


def retry_errors(df, dims, tax, prompt_tpl, llm, limiter,
                 max_workers, title_col, abstract_col, keywords_col):
    dc = [c for c in df.columns if c.endswith("_category")]
    if not dc:
        return df
    err = df.index[df[dc[0]] == "ERROR"].tolist()
    if not err:
        logger.info("无 ERROR", "No ERROR found")
        return df
    logger.info(f"重测 {len(err)} 条", f"Retrying {len(err)} entries")

    dims_desc = _build_dims_desc(dims, tax)
    lock = threading.Lock()

    def worker(idx):
        row = df.loc[idx]
        pt = build_paper(row, title_col, abstract_col, keywords_col)
        dim_map = {f"dim{i+1}_name": dim["name"] for i, dim in enumerate(dims)}
        limiter.wait()
        result = llm.chat_json([{"role": "user", "content": render_prompt(prompt_tpl,
            dimensions_desc=dims_desc, paper_text=pt, **dim_map,
        )}])
        return idx, result

    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        pbar = tqdm(total=len(err), desc="Retrying", unit="entry")
        for fut in as_completed({ex.submit(worker, i): i for i in err}):
            idx, result = fut.result()
            if result:
                with lock:
                    df.at[idx, "is_review"] = result.get("是否综述性论文", "")
                    df.at[idx, "review_evidence"] = result.get("综述判断依据", "")
                    for dim in dims:
                        p = dim.get("prefix", dim["name"][:4])
                        d = result.get(dim["name"], {})
                        for c, k in [("category", "大类"), ("subcategory", "子类"),
                                      ("evidence", "依据"), ("sub_evidence", "细化依据"),
                                      ("reason", "理由")]:
                            df.at[idx, f"{p}_{c}"] = d.get(k, "")
            pbar.update(1)
        pbar.close()
    return df


def _build_dims_desc(dims, tax):
    lines = []
    for dim in dims:
        lines.append(f"\n### 维度: {dim['name']}")
        for cat in dim.get("categories", []):
            lines.append(f"- 大类: {cat}")
            subs = tax.get(dim["name"], {}).get(cat, [])
            for s in subs:
                if isinstance(s, dict):
                    name = s.get("name", "")
                    definition = s.get("definition", "")
                    judgment = s.get("judgment_suggestions", "")
                    lines.append(f"  * 子类: {name}")
                    if definition:
                        lines.append(f"    - 定义: {definition}")
                    if judgment:
                        lines.append(f"    - 判定建议: {judgment}")
                else:
                    lines.append(f"  * 子类: {s}")
    return "\n".join(lines)

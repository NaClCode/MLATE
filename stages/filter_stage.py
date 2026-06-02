"""筛选阶段：先抽样探索评分标准 → 再逐篇评分 → 筛选展示"""
import random, json
import pandas as pd
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor
from utils import safe_str, build_paper, render_prompt
from logger import logger


def run_filter(df, topic, min_score, llm, limiter, max_workers,
               title_col, abstract_col, keywords_col,
               prompt_criteria, prompt_score, output_lang="中文"):
    """两步法：1) 抽样探索评分标准  2) 逐篇评分 + 筛选"""
    total = len(df)
    logger.info(f"原始论文: {total} 篇", f"Total papers: {total}")
    logger.info(f"主题: {topic}", f"Topic: {topic}")

    # ── 第一步：抽样探索评分标准 ──
    sample_n = min(15, total)
    sample_df = df.sample(n=sample_n, random_state=42)
    logger.section(f"第一步：抽取 {sample_n} 篇样本探索评分标准...", 
                   f"Step 1: Sampling {sample_n} papers to explore scoring criteria...")

    samples_text = "\n".join(
        f"#{i+1} {build_paper(sample_df.iloc[i], title_col, abstract_col, keywords_col)}"
        for i in range(len(sample_df))
    )
    limiter.wait()
    criteria_result = llm.chat_json([{"role": "user", "content": render_prompt(prompt_criteria,
        sample_count=sample_n, topic=topic, samples_text=samples_text, output_lang=output_lang
    )}])

    if criteria_result:
        logger.info(f"  样本分析: {criteria_result.get('样本分析', '')[:120]}...")
        std = criteria_result.get("评分标准", {})
        for s in ["5", "4", "3", "2", "1"]:
            if s in std:
                logger.info(f"    {s}分: {std[s][:60]}...")
        # 导出评分标准文本供第二步使用
        criteria_text = json.dumps(std, ensure_ascii=False)
    else:
        logger.warning("标准探索失败，使用默认评分规则", "Criteria exploration failed, using default rules")
        criteria_text = (
            '{"5":"高度相关且核心贡献","4":"相关","3":"部分相关","2":"弱相关","1":"不相关"}'
        )

    # ── 第二步：逐篇评分 ──
    logger.section(f"第二步：逐篇评分（共 {total} 篇）...", f"Step 2: Scoring {total} papers one by one...")
    scores = [None] * total

    def worker(idx):
        row = df.iloc[idx]
        pt = build_paper(row, title_col, abstract_col, keywords_col)
        limiter.wait()
        return idx, llm.chat_json([{"role": "user", "content": render_prompt(prompt_score,
            topic=topic, criteria=criteria_text, paper_text=pt, output_lang=output_lang
        )}])

    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        # 使用 tqdm 显示进度条
        pbar = tqdm(total=total, desc="Scoring", unit="paper")
        for idx, result in ex.map(worker, range(total)):
            scores[idx] = result
            pbar.update(1)
        pbar.close()

    # 写入评分
    df["score"] = [s.get("score", 1) if s else 1 for s in scores]
    df["reason"] = [s.get("reason", "") if s else "" for s in scores]
    df["keywords"] = [s.get("keywords", "") if s else "" for s in scores]
    df["passed"] = df["score"] >= min_score

    # 统计
    from collections import Counter
    cnt = Counter(df["score"])
    logger.section("评分分布", "Score Distribution")
    for k in sorted(cnt):
        logger.info(f"  {k}分: {cnt[k]} ({cnt[k]/total*100:.1f}%)")

    # 输出统计信息
    passed_count = df["passed"].sum()
    logger.info(f"筛选统计 (≥{min_score}分): {passed_count}/{total} 篇通过", 
                f"Filter Stats (≥{min_score}): {passed_count}/{total} papers passed")
    
    # 返回包含所有评分信息的完整 DataFrame
    return df

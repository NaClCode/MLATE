"""MLATE CLI 入口"""
import argparse
from pipeline import MLATEPipeline
import config
from logger import logger


def main():
    parser = argparse.ArgumentParser(prog="mlate", description="Multi-dimensional Literature Analysis and Thematic Exploration")
    g = parser.add_argument_group("全局选项")
    g.add_argument("--api-base", help="API Base URL")
    g.add_argument("--model", default=None, help="模型名（默认按配置文件/环境变量/模型推断）")
    g.add_argument("--workers", type=int, default=8)
    g.add_argument("--qps", type=float, default=2.0)
    g.add_argument("--lang", choices=["cn", "en", "both"], help="Output language (cn/en/both)")
    g.add_argument("--source", choices=["auto", "wos", "scopus", "standard"], default="auto", 
                   help="Data source type (auto-detect, wos, scopus, standard)")

    sub = parser.add_subparsers(dest="command", required=True)

    # ── config ──
    pc = sub.add_parser("config", help="管理配置（API Key / Base URL / Model）")
    pc.add_argument("action", choices=["init", "set", "get", "show"],
                    help="init=初始化 | set=设置值 key value | get=读取值 key | show=查看全部")
    pc.add_argument("args", nargs="*", help="set 需要 key value；get 需要 key")

    # ── filter ──
    pf = sub.add_parser("filter", help="主题筛选：LLM 按用户主题评分排名，筛选 ≥ min-score")
    pf.add_argument("--input", required=True)
    pf.add_argument("--output", required=True)
    pf.add_argument("--topic", required=True, help="筛选主题，如 'ship digital twin propulsion'")
    pf.add_argument("--min-score", type=float, default=3.0, help="最低评分（1-5），默认 3.0")

    # ── explore ──
    pe = sub.add_parser("explore", help="主题探索：第一阶段（自发发现草案 - 逐篇分析）")
    pe.add_argument("--input", required=True, help="筛选后的 CSV 输入")
    pe.add_argument("--output", required=True, help="输出原始草案 JSON 路径")
    pe.add_argument("--max-papers", type=int)
    pe.add_argument("--dims", help="初始维度（逗号分隔）")
    pe.add_argument("--guide", help="研究者引导词")

    # ── converge ──
    pcv = sub.add_parser("converge", help="主题探索：第二阶段（智能收敛与总结）")
    pcv.add_argument("--input", required=True, help="explore 产出的原始草案 JSON")
    pcv.add_argument("--output", required=True, help="输出最终收敛后的 taxonomy JSON")
    pcv.add_argument("--output-csv", help="输出带标签的文献 CSV 路径")
    pcv.add_argument("--limit-cats", type=int, default=10, help="每个维度保留的分类上限")
    pcv.add_argument("--dims", help="指定收敛的维度（默认全量）")
    pcv.add_argument("--guide", help="收敛阶段的引导词")
    pcv.add_argument("--source-csv", help="可选：原始 CSV 路径（用于将 ID 映射回论文标题）")

    args = parser.parse_args()

    # Set language: Priority CLI > Config > Env (Default: en)
    cfg = config.load()
    lang = args.lang or cfg.get("lang")
    if lang:
        logger.set_lang(lang)

    # 处理 config 子命令（不需要 pipeline）
    if args.command == "config":
        # 重新配置 argparse 以支持 config get <key>
        config.cmd_config(args)
        return

    pipe = MLATEPipeline(
        model=args.model, api_base=args.api_base,
        max_workers=args.workers, qps=args.qps,
    )

    if args.command == "filter":
        pipe.filter(args.input, args.output, topic=args.topic, min_score=args.min_score, source_type=args.source)
    elif args.command == "explore":
        pipe.explore(args.input, args.output, args.max_papers, 
                     source_type=args.source, researcher_guide=args.guide,
                     initial_dims=args.dims)
    elif args.command == "converge":
        pipe.converge(args.input, args.output, limit_cats=args.limit_cats,
                      target_dims=args.dims, researcher_guide=args.guide,
                      source_csv=args.source_csv, output_csv=args.output_csv)


if __name__ == "__main__":
    main()

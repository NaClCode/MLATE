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
    pe = sub.add_parser("explore", help="主题探索（批次细化）")
    pe.add_argument("--input", required=True)
    pe.add_argument("--output", required=True, help="输出 taxonomy JSON 路径")
    pe.add_argument("--batch-size", type=int, default=20)
    pe.add_argument("--max-papers", type=int)
    pe.add_argument("--guide", help="研究者引导词（例如设定主体方向、提供参考示例等）")

    # ── analyze ──
    pa = sub.add_parser("analyze", help="逐篇维度分析")
    pa.add_argument("--input", required=True)
    pa.add_argument("--output", required=True)
    pa.add_argument("--taxonomy", help="taxonomy JSON 文件路径")
    pa.add_argument("--max-papers", type=int)

    # ── retry ──
    pr = sub.add_parser("retry", help="错误重试")
    pr.add_argument("--input", required=True)
    pr.add_argument("--output")

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
        pipe.explore(args.input, args.output, args.batch_size, args.max_papers, 
                     source_type=args.source, researcher_guide=args.guide)
    elif args.command == "analyze":
        pipe.analyze(args.input, args.output, args.taxonomy, args.max_papers, source_type=args.source)
    elif args.command == "retry":
        pipe.retry(args.input, args.output)


if __name__ == "__main__":
    main()

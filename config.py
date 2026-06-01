"""Configuration management: ~/.mlate/config.json + Env var auto-detection

Security Design:
  - API Keys are NEVER stored on disk.
  - API Keys must be provided via environment variables (MLATE_API_KEY) or CLI arguments.
  - Base URL and Model are non-sensitive and can be persisted safely.
"""
import os, json, sys, shutil
from pathlib import Path
from logger import logger

CONFIG_DIR = Path.home() / ".mlate"
CONFIG_FILE = CONFIG_DIR / "config.json"
# Priority for env vars
ENV_KEY_PRIORITY = ["MLATE_API_KEY", "LLM_API_KEY", "OPENAI_API_KEY", "DEEPSEEK_API_KEY"]


def _ensure_dir():
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if sys.platform != "win32":
        CONFIG_DIR.chmod(0o700)


def load() -> dict:
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def save(cfg: dict):
    _ensure_dir()
    tmp = CONFIG_FILE.with_suffix(".tmp")
    with open(tmp, "w") as f:
        json.dump(cfg, f, indent=2)
    if sys.platform != "win32":
        tmp.chmod(0o600)
    tmp.rename(CONFIG_FILE)


def mask_key(key: str) -> str:
    if len(key) <= 12:
        return "****"
    return key[:8] + "…" + key[-4:]


def resolve_api_key() -> str:
    """Resolution: Env vars only. (Security policy: No CLI or Config file storage)"""
    for var in ENV_KEY_PRIORITY:
        v = os.environ.get(var)
        if v:
            return v
    return ""


def resolve_base_url(model: str, cli_value: str | None = None) -> str:
    if cli_value:
        return cli_value
    env = os.environ.get("MLATE_API_BASE")
    if env:
        return env
    cfg = load()
    cfg_base = cfg.get("api_base")
    if cfg_base:
        return cfg_base
    m = model.lower()
    if any(k in m for k in ["deepseek"]):
        return "https://api.deepseek.com"
    if any(k in m for k in ["gpt", "o1", "o3"]):
        return "https://api.openai.com/v1"
    return "https://api.deepseek.com"


def resolve_model(cli_value: str | None = None) -> str:
    if cli_value:
        return cli_value
    env = os.environ.get("MLATE_MODEL")
    if env:
        return env
    cfg = load()
    return cfg.get("model", "deepseek-chat")


# ── CLI 交互 ──────────────────────────────────────────────────
def _print_setup_guide():
    logger.info("")
    logger.info("=" * 54)
    logger.info("  API Key not set. Please use environment variables:", "  API Key 未设置，请通过环境变量配置：")
    logger.info("")
    logger.info("  Set environment variable (Recommended):", "  设置环境变量（推荐）：")
    logger.info("     $env:MLATE_API_KEY = \"sk-xxx\"    # Windows PowerShell")
    logger.info('     export MLATE_API_KEY="sk-xxx"       # Linux/macOS')
    logger.info("=" * 54)


def cmd_config(args):
    action = args.action
    rest = args.args

    if action == "init":
        _ensure_dir()
        if not CONFIG_FILE.exists():
            save({})
            logger.success(f"Created {CONFIG_FILE}", f"已创建 {CONFIG_FILE}")
        else:
            logger.info(f"Already exists: {CONFIG_FILE}", f"已存在: {CONFIG_FILE}")

    elif action == "set":
        if len(rest) < 2:
            logger.info("Usage: mlate config set <key> <value>", "用法: mlate config set <key> <value>")
            logger.info("  Keys: api_base, model, lang", "  可用键: api_base, model, lang")
            return
        key, value = rest[0], rest[1]
        if key == "api_key":
            logger.error("Security policy: api_key cannot be stored in config file.", 
                         "安全策略：api_key 不支持存储在配置文件中。")
            logger.info("Please use environment variable MLATE_API_KEY instead.", 
                         "请改用环境变量 MLATE_API_KEY。")
            return
        cfg = load()
        cfg[key] = value
        save(cfg)
        logger.success(f"Successfully set {key}", f"已设置 {key}")

    elif action == "get":
        if not rest:
            logger.info("Usage: mlate config get <key>", "用法: mlate config get <key>")
            logger.info("  Keys: api_base, model, lang", "  可用键: api_base, model, lang")
            return
        key = rest[0]
        if key == "api_key":
            print(resolve_api_key())
            return
        cfg = load()
        print(cfg.get(key, ""))

    elif action == "show":
        logger.info(f"Config file: {CONFIG_FILE}", f"配置文件: {CONFIG_FILE}")
        logger.info(f"Env variable: MLATE_API_KEY", f"环境变量: MLATE_API_KEY")
        logger.info("")
        model = resolve_model()
        base = resolve_base_url(model)
        key = resolve_api_key()
        key_source_cn = "环境变量" if key else "无"
        key_source_en = "Env Var" if key else "None"
        
        logger.info("Current effective configuration:", "当前生效配置:")
        logger.info(f"  model    = {model}")
        logger.info(f"  api_base = {base}")
        logger.info(f"  api_key  = {'[Set]' if key else '[Not Set]'} ({key_source_en})",
                    f"  api_key  = {'[已设置]' if key else '[未设置]'} ({key_source_cn})")
        logger.info("")
        cfg = load()
        if "api_key" in cfg:
            del cfg["api_key"] # Clean up legacy key if exists
            save(cfg)
            
        if cfg:
            logger.info(f"Config file content ({len(cfg)} items):", f"配置文件内容 ({len(cfg)} 项):")
            for k, v in cfg.items():
                logger.info(f"  {k} = {v}")
        else:
            logger.info("Config file is empty", "配置文件为空")

        if not key:
            _print_setup_guide()

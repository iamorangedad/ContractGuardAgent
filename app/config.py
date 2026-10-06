import copy
import os
from pathlib import Path
import yaml
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = BASE_DIR / "config.yaml"

default_config = {
    "app": {
        "host": "0.0.0.0",
        "port": 8000,
        "debug": False
    },
    "database": {
        "path": "app/data/contracts.db"
    },
    "llm": {
        "provider": "ollama",
        "model": "llama3.2",
        "temperature": 0.1,
        "base_url": "http://localhost:11434",
        "use_llm": True
    },
    "embeddings": {
        "model": "text-embedding-3-small",
        "use_embeddings": False
    },
    "task": {
        "max_retries": 3,
        "retry_delay": 2
    },
    "logging": {
        "level": "INFO",
        "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    }
}

def load_config() -> dict:
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            user_config = yaml.safe_load(f) or {}
        
        config = copy.deepcopy(default_config)
        for section, values in user_config.items():
            if section in config:
                config[section].update(values)
            else:
                config[section] = values
        return config
    
    return default_config

def _env_flag(name: str):
    raw = os.getenv(name)
    if raw is None:
        return None
    return raw.strip().lower() in ("1", "true", "yes", "on")


def apply_env_overrides(config: dict) -> dict:
    """环境变量覆盖配置文件，进程内只认这一份结果。"""
    merged = {key: (dict(value) if isinstance(value, dict) else value) for key, value in config.items()}

    if os.getenv("DATABASE_PATH"):
        merged.setdefault("database", {})["path"] = os.getenv("DATABASE_PATH")

    llm = merged.setdefault("llm", {})
    use_llm = _env_flag("USE_LLM")
    if use_llm is not None:
        llm["use_llm"] = use_llm
    if os.getenv("LLM_PROVIDER"):
        llm["provider"] = os.getenv("LLM_PROVIDER")
    if os.getenv("LLM_MODEL"):
        llm["model"] = os.getenv("LLM_MODEL")
    if os.getenv("LLM_BASE_URL"):
        llm["base_url"] = os.getenv("LLM_BASE_URL")

    embeddings = merged.setdefault("embeddings", {})
    use_embeddings = _env_flag("USE_EMBEDDINGS")
    if use_embeddings is not None:
        embeddings["use_embeddings"] = use_embeddings

    return merged


def get_config() -> dict:
    if not hasattr(get_config, "_base"):
        get_config._base = load_config()
    return apply_env_overrides(get_config._base)

def save_config(config: dict):
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        yaml.dump(config, f, allow_unicode=True)
    get_config._base = config

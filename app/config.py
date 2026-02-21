import os
from pathlib import Path
import yaml

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
        "temperature": 0.3,
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
        
        config = default_config.copy()
        for section, values in user_config.items():
            if section in config:
                config[section].update(values)
            else:
                config[section] = values
        return config
    
    return default_config

def get_config() -> dict:
    if not hasattr(get_config, '_config'):
        get_config._config = load_config()
    return get_config._config

def save_config(config: dict):
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        yaml.dump(config, f, allow_unicode=True)
    get_config._config = config

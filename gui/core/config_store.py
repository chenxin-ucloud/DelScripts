"""配置持久化模块：保存/加载用户配置到 ~/.ucloud_cleaner/config.json

出于安全考虑，私钥（private_key）不会持久化到磁盘，每次启动需手动填写。
"""
import json
import logging
import os
from dataclasses import asdict
from typing import Optional

from core.state import AppState

logger = logging.getLogger(__name__)

CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".ucloud_cleaner")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")

# 不持久化的字段（敏感信息）
SENSITIVE_FIELDS = {"private_key"}


def save_config(state: AppState) -> None:
    """将 AppState 保存到 config.json，跳过敏感字段"""
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        data = asdict(state)
        for field_name in SENSITIVE_FIELDS:
            data.pop(field_name, None)

        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except OSError as e:
        logger.warning(f"保存配置失败: {e}")


def load_config() -> Optional[dict]:
    """从 config.json 加载配置，返回 dict 或 None"""
    if not os.path.exists(CONFIG_FILE):
        return None
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        logger.warning(f"加载配置失败: {e}")
        return None


def apply_config_to_state(state: AppState, data: dict) -> None:
    """将加载的配置字典应用到 AppState（容错：未知字段忽略，缺失字段保留默认值）"""
    if not data:
        return
    for key, value in data.items():
        if key in SENSITIVE_FIELDS:
            continue
        if hasattr(state, key):
            try:
                setattr(state, key, value)
            except Exception:
                pass

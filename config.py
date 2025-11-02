"""Configuration utilities for the Telegram gallery bot."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

CONFIG_PATH_ENV = "BOT_CONFIG_PATH"


@dataclass(frozen=True)
class TelegraphSettings:
    """Telegraph API credentials and optional author metadata."""

    access_tokens: Tuple[str, ...]
    author_name: Optional[str] = None
    author_url: Optional[str] = None


@dataclass(frozen=True)
class BotConfig:
    """Runtime configuration for the Telegram bot."""

    telegram_bot_token: str
    telegraph: TelegraphSettings
    ehentai_cookies: Dict[str, str]


class ConfigError(RuntimeError):
    """Raised when the configuration file is invalid."""


def _load_raw_config(path: Path) -> Dict[str, object]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except FileNotFoundError as exc:
        raise ConfigError(f"配置文件未找到：{path}") from exc
    except json.JSONDecodeError as exc:
        raise ConfigError(f"配置文件格式错误：{path}") from exc


def load_config(path: Optional[str] = None) -> BotConfig:
    """Load configuration from the given path or default location."""

    config_path = Path(path or os.environ.get(CONFIG_PATH_ENV, "config.json"))
    data = _load_raw_config(config_path)

    try:
        telegram_token = str(data["telegram_bot_token"])
    except KeyError as exc:
        raise ConfigError("缺少字段：telegram_bot_token") from exc

    telegraph_data = data.get("telegraph")
    if not isinstance(telegraph_data, dict):
        raise ConfigError("缺少 telegraph 配置")

    tokens_data = telegraph_data.get("access_tokens")
    tokens: List[str] = []
    if isinstance(tokens_data, list):
        for token in tokens_data:
            token_str = str(token).strip()
            if token_str:
                tokens.append(token_str)
        if not tokens:
            raise ConfigError("telegraph.access_tokens 不能为空")
    elif tokens_data is not None:
        raise ConfigError("telegraph.access_tokens 必须为数组")
    else:
        try:
            single_token = str(telegraph_data["access_token"])
        except KeyError as exc:
            raise ConfigError("缺少字段：telegraph.access_tokens 或 telegraph.access_token") from exc
        if not single_token:
            raise ConfigError("telegraph.access_token 不能为空")
        tokens = [single_token]

    telegraph_author_name = telegraph_data.get("author_name")
    telegraph_author_url = telegraph_data.get("author_url")

    cookies_data = data.get("ehentai_cookies")
    if not isinstance(cookies_data, dict) or not cookies_data:
        raise ConfigError("缺少 ehentai_cookies 配置")

    cookies: Dict[str, str] = {str(key): str(value) for key, value in cookies_data.items()}

    return BotConfig(
        telegram_bot_token=telegram_token,
        telegraph=TelegraphSettings(
            access_tokens=tuple(tokens),
            author_name=str(telegraph_author_name) if telegraph_author_name else None,
            author_url=str(telegraph_author_url) if telegraph_author_url else None,
        ),
        ehentai_cookies=cookies,
    )


__all__ = ["BotConfig", "TelegraphSettings", "ConfigError", "load_config"]

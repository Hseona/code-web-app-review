"""Configuration helpers for Claude integration."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Dict


class ClaudeSettings:
    """Load Claude integration settings from environment or local dotenv files."""

    def __init__(self, env: Dict[str, str]) -> None:
        self._env = env

        self.api_key = self._get("CLAUDE_API_KEY") or self._get("ANTHROPIC_API_KEY")
        self.base_url = self._get("CLAUDE_API_URL", default="https://api.anthropic.com")
        self.model = self._get("CLAUDE_MODEL", default="claude-3-haiku-20240307")
        self.timeout_seconds = int(self._get("CLAUDE_TIMEOUT_SECONDS", default="30"))
        self.max_attempts = int(self._get("CLAUDE_MAX_ATTEMPTS", default="3"))
        self.retry_delay_seconds = float(self._get("CLAUDE_RETRY_DELAY_SECONDS", default="0.5"))
        self.max_tokens = int(self._get("CLAUDE_MAX_TOKENS", default="2048"))
        self.temperature = float(self._get("CLAUDE_TEMPERATURE", default="0.0"))

    def _get(self, key: str, *, default: str | None = None) -> str | None:
        if key in os.environ:
            return os.environ[key]
        if key in self._env:
            return self._env[key]
        return default


def _load_dotenv(*paths: str) -> Dict[str, str]:
    env_map: Dict[str, str] = {}
    for path in paths or (".env", ".env.local"):
        dotenv_path = Path(path)
        if not dotenv_path.is_file():
            continue

        for raw_line in dotenv_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            parsed_value = value.strip().strip('"').strip("'")
            env_map[key.strip()] = parsed_value
    return env_map

# todo 기존과 다른 변경사항이 생긴 경우 캐시 비우는 로직 추가 필요
@lru_cache()
def get_settings() -> ClaudeSettings:
    return ClaudeSettings(_load_dotenv(".env", ".env.local"))

"""환경변수 + 상수."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"

load_dotenv(PROJECT_ROOT / ".env")


def _required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"환경변수 누락: {name}")
    return value


def _optional_int(name: str, default: int) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    return int(raw)


def _optional_id(name: str) -> int | None:
    raw = os.getenv(name, "").strip()
    if not raw:
        return None
    return int(raw)


@dataclass(frozen=True)
class Settings:
    discord_token: str
    guild_id: int | None
    apply_channel_id: int
    log_channel_id: int | None
    reset_hour: int
    draw_hour: int
    draw_minute: int
    deadline_hour: int
    team_slots: int
    data_dir: Path


def load_settings() -> Settings:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return Settings(
        discord_token=_required("DISCORD_TOKEN"),
        guild_id=_optional_id("GUILD_ID"),
        apply_channel_id=int(_required("APPLY_CHANNEL_ID")),
        log_channel_id=_optional_id("LOG_CHANNEL_ID"),
        reset_hour=_optional_int("RESET_HOUR", 21),
        draw_hour=_optional_int("DRAW_HOUR", 0),
        draw_minute=_optional_int("DRAW_MINUTE", 30),
        deadline_hour=_optional_int("DEADLINE_HOUR", 17),
        team_slots=_optional_int("TEAM_SLOTS", 8),
        data_dir=DATA_DIR,
    )


SETTINGS = load_settings()

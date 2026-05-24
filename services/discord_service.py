"""Discord 채널/메시지 헬퍼."""
from __future__ import annotations

import logging
from pathlib import Path

import discord

from models.storage import read_json, write_json

logger = logging.getLogger(__name__)


def load_message_id(path: Path) -> int | None:
    raw = read_json(path, default={})
    value = raw.get("message_id")
    return int(value) if value else None


def save_message_id(path: Path, message_id: int) -> None:
    write_json(path, {"message_id": message_id})


async def fetch_text_channel(bot: discord.Client, channel_id: int) -> discord.TextChannel:
    channel = bot.get_channel(channel_id)
    if channel is None:
        channel = await bot.fetch_channel(channel_id)
    if not isinstance(channel, discord.TextChannel):
        raise RuntimeError(f"채널 {channel_id}은 텍스트 채널이 아닙니다.")
    return channel


async def fetch_message_safe(channel: discord.TextChannel, message_id: int) -> discord.Message | None:
    try:
        return await channel.fetch_message(message_id)
    except (discord.NotFound, discord.Forbidden):
        return None
    except discord.HTTPException as exc:
        logger.warning("메시지 fetch 실패 channel=%s message=%s err=%s", channel.id, message_id, exc)
        return None

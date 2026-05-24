"""봇 라이프사이클 헬퍼."""
from __future__ import annotations

import asyncio
import logging
import signal

from bot.client import KelBot
from config.settings import Settings

logger = logging.getLogger(__name__)


async def run_bot(settings: Settings) -> None:
    bot = KelBot(settings)
    loop = asyncio.get_running_loop()

    def _shutdown() -> None:
        logger.info("종료 시그널 수신 — 봇 종료")
        if bot.schedule is not None:
            bot.schedule.stop()
        asyncio.create_task(bot.close())

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _shutdown)
        except NotImplementedError:
            # Windows
            pass

    try:
        await bot.start(settings.discord_token)
    finally:
        if not bot.is_closed():
            await bot.close()

"""kelbot 진입점."""
from __future__ import annotations

import asyncio
import logging

from bot.manager import run_bot
from config.logging_config import setup_logging
from config.settings import PROJECT_ROOT, SETTINGS


def main() -> None:
    setup_logging(log_path=PROJECT_ROOT / "kelbot.log")
    logger = logging.getLogger("kelbot")
    logger.info("kelbot 시작")
    asyncio.run(run_bot(SETTINGS))


if __name__ == "__main__":
    main()

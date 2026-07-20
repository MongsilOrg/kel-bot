"""kelbot 진입점."""
from __future__ import annotations

import asyncio
import logging
import os

import sentry_sdk

from bot.manager import run_bot
from config.logging_config import setup_logging
from config.settings import PROJECT_ROOT, SETTINGS  # import 시점에 load_dotenv() 실행

# 장애 추적. settings import로 .env가 로드된 뒤여야 DSN이 잡힌다.
# DSN이 비어 있으면 transport가 없어 어디로도 전송되지 않는다.
sentry_sdk.init(
    dsn=os.getenv("SENTRY_DSN", ""),
    traces_sample_rate=0.1,
    environment="production",
)


def main() -> None:
    setup_logging(log_path=PROJECT_ROOT / "kelbot.log")
    logger = logging.getLogger("kelbot")
    logger.info("kelbot 시작")
    asyncio.run(run_bot(SETTINGS))


if __name__ == "__main__":
    main()

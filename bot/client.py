"""kelbot 클라이언트."""
from __future__ import annotations

import logging
from typing import Optional

import discord
from discord.ext import commands

from commands.dashboard import DashboardController
from config.settings import Settings
from models.schedule_manager import ScheduleManager

logger = logging.getLogger(__name__)


class KelBot(commands.Bot):
    """KEL 스크림 봇 — 슬래시 명령어 없음, 대시보드 전용."""

    def __init__(self, settings: Settings) -> None:
        intents = discord.Intents.default()
        intents.message_content = False
        intents.members = True
        super().__init__(command_prefix="!kel_unused_", intents=intents, help_command=None)
        self.settings = settings
        self.schedule: Optional[ScheduleManager] = None
        self.dashboard: Optional[DashboardController] = None

    async def setup_hook(self) -> None:
        self.dashboard = None  # setup 후 채워짐

        async def on_draw(result):
            assert self.dashboard is not None
            await self.dashboard.announce_draw(result)

        async def on_state_changed():
            if self.dashboard is not None:
                await self.dashboard.refresh()

        async def on_deadline_cancelled():
            if self.dashboard is not None:
                await self.dashboard.announce_deadline_cancelled()

        self.schedule = ScheduleManager(
            settings=self.settings,
            data_dir=self.settings.data_dir,
            on_draw=on_draw,
            on_state_changed=on_state_changed,
            on_deadline_cancelled=on_deadline_cancelled,
        )
        self.dashboard = DashboardController(self, self.settings, self.schedule)
        # tasks.loop는 client loop이 준비된 시점에 start 해야 함 → on_ready에서

    async def on_ready(self) -> None:
        assert self.schedule is not None and self.dashboard is not None
        logger.info("로그인 완료: %s (%s)", self.user, self.user.id if self.user else "?")
        await self.dashboard.setup()
        await self.schedule.catch_up()
        self.schedule.start()
        logger.info("스케줄러 가동 — 23:00 리셋 / 00:30 추첨 / 17:00 데드라인 KST")

"""스케줄러 + 재시작 시 놓친 이벤트 보정."""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import date as date_cls
from datetime import time, timedelta
from pathlib import Path
from typing import Awaitable, Callable

from discord.ext import tasks

from config.settings import Settings
from models.application import ApplicationStore
from models.draw_orchestrator import DrawOrchestrator, DrawResult
from models.draw_state import DrawState, DrawStatus
from models.priority import PriorityStore
from models.priority_audit import PriorityAuditStore
from utils.time import KST, current_scrim_date, kst_at, now_kst

logger = logging.getLogger(__name__)


DrawCallback = Callable[[DrawResult], Awaitable[None]]
SimpleCallback = Callable[[], Awaitable[None]]


@dataclass
class StateBundle:
    applications: ApplicationStore
    priorities: PriorityStore
    draw_state: DrawState
    audit: PriorityAuditStore


class ScheduleManager:
    """일일 운영 스케줄 + 재시작 보정.

    - 21:00 일일 리셋
    - 00:30 1차 추첨 (미달 시 보류)
    - 17:00 데드라인 (미달 취소 + 우선권 소멸)
    - 신청/취소 이벤트 시 즉시 추첨 트리거
    """

    def __init__(
        self,
        settings: Settings,
        data_dir: Path,
        on_draw: DrawCallback,
        on_state_changed: SimpleCallback,
        on_deadline_cancelled: SimpleCallback,
        on_reset: SimpleCallback,
    ) -> None:
        self.settings = settings
        self.data_dir = data_dir
        self.on_draw = on_draw
        self.on_state_changed = on_state_changed
        self.on_deadline_cancelled = on_deadline_cancelled
        self.on_reset = on_reset

        self._lock = asyncio.Lock()
        scrim_date = current_scrim_date(self.settings.reset_hour).isoformat()
        self._state = StateBundle(
            applications=ApplicationStore.load(data_dir / "applications.json", scrim_date),
            priorities=PriorityStore.load(data_dir / "priorities.json"),
            draw_state=DrawState.load(data_dir / "draw_state.json", scrim_date),
            audit=PriorityAuditStore.load(data_dir / "priority_audit.json"),
        )

        self._reset_task = tasks.loop(time=time(hour=21, minute=0, tzinfo=KST))(self._run_reset)
        self._draw_task = tasks.loop(time=time(hour=0, minute=30, tzinfo=KST))(self._run_draw)
        self._deadline_task = tasks.loop(time=time(hour=17, minute=0, tzinfo=KST))(self._run_deadline)

    # 외부 접근 ------------------------------------------------------------
    @property
    def state(self) -> StateBundle:
        return self._state

    @property
    def lock(self) -> asyncio.Lock:
        return self._lock

    def orchestrator(self) -> DrawOrchestrator:
        return DrawOrchestrator(
            self._state.applications,
            self._state.priorities,
            self._state.draw_state,
            self.settings.team_slots,
        )

    # 부팅 시 보정 ----------------------------------------------------------
    async def catch_up(self) -> None:
        async with self._lock:
            await self._catch_up_locked()
        await self.on_state_changed()

    async def _catch_up_locked(self) -> None:
        time_based = current_scrim_date(self.settings.reset_hour).isoformat()
        # 저장된 일자가 과거면 시간 기준으로 catch-up (놓친 리셋). 미래/현재면 그대로.
        if self._state.draw_state.scrim_date < time_based:
            logger.info("놓친 리셋 catch-up — %s → %s", self._state.draw_state.scrim_date, time_based)
            self._reset_to(time_based)
        scrim_date = self._state.draw_state.scrim_date
        self._state.priorities.purge_outdated(scrim_date)
        self._state.audit.purge_outdated(scrim_date)

        moment = now_kst()
        scrim_date_obj = date_cls.fromisoformat(scrim_date)
        draw_at = kst_at(scrim_date_obj, self.settings.draw_hour, self.settings.draw_minute)
        deadline_at = kst_at(scrim_date_obj, self.settings.deadline_hour, 0)

        if moment >= draw_at and self._state.draw_state.status == DrawStatus.PENDING:
            result = self.orchestrator().attempt_primary_draw()
            if result is not None:
                await self.on_draw(result)

        if self._state.draw_state.status == DrawStatus.HELD:
            result = self.orchestrator().attempt_instant_draw()
            if result is not None:
                await self.on_draw(result)

        if moment >= deadline_at and not self._state.draw_state.deadline_processed:
            cancelled = self.orchestrator().force_deadline_cancel()
            if cancelled:
                self._early_reset_to_next_day()
                await self.on_deadline_cancelled()

        # 부팅 직전 미진행 확정 상태로 종료된 경우 D+1로 전환 (안전망)
        if (
            self._state.draw_state.status == DrawStatus.CANCELLED
            and moment >= deadline_at
        ):
            self._early_reset_to_next_day()

    def _reset_to(self, scrim_date: str) -> bool:
        """주어진 scrim_date로 application/draw_state 리셋. 같은 일자면 no-op.

        실제로 초기화했으면 True, 이미 같은 일자라 no-op이면 False를 반환한다.
        """
        if (
            self._state.applications.scrim_date == scrim_date
            and self._state.draw_state.scrim_date == scrim_date
        ):
            return False
        self._state.applications.reset(scrim_date)
        self._state.draw_state.reset(scrim_date)
        return True

    def _early_reset_to_next_day(self) -> None:
        """미진행 확정(17:00) 직후 D+1로 즉시 전환."""
        current = self._state.draw_state.scrim_date
        next_date = (date_cls.fromisoformat(current) + timedelta(days=1)).isoformat()
        logger.info("미진행 확정 → 즉시 D+1 리셋: %s → %s", current, next_date)
        self._reset_to(next_date)
        self._state.priorities.purge_outdated(next_date)
        self._state.audit.purge_outdated(next_date)

    # 이벤트 트리거 ---------------------------------------------------------
    async def trigger_instant_draw_if_ready(self) -> None:
        async with self._lock:
            result = self.orchestrator().attempt_instant_draw()
        if result is not None:
            await self.on_draw(result)

    # 스케줄러 라이프사이클 -------------------------------------------------
    def start(self) -> None:
        if not self._reset_task.is_running():
            self._reset_task.start()
        if not self._draw_task.is_running():
            self._draw_task.start()
        if not self._deadline_task.is_running():
            self._deadline_task.start()

    def stop(self) -> None:
        for t in (self._reset_task, self._draw_task, self._deadline_task):
            if t.is_running():
                t.cancel()

    async def _run_reset(self) -> None:
        async with self._lock:
            scrim_date = current_scrim_date(self.settings.reset_hour).isoformat()
            changed = self._reset_to(scrim_date)
            self._state.priorities.purge_outdated(scrim_date)
            self._state.audit.purge_outdated(scrim_date)
            if changed:
                logger.info("일일 리셋 실행 → %s", scrim_date)
            else:
                logger.info("일일 리셋 시각 — 이미 %s로 초기화됨(조기초기화), 스킵", scrim_date)
        # 실제 초기화된 경우에만 대시보드 메시지 재생성 (조기초기화로 no-op이면 스킵)
        if changed:
            await self.on_reset()

    async def _run_draw(self) -> None:
        async with self._lock:
            result = self.orchestrator().attempt_primary_draw()
        if result is not None:
            await self.on_draw(result)
        else:
            await self.on_state_changed()

    async def _run_deadline(self) -> None:
        async with self._lock:
            cancelled = self.orchestrator().force_deadline_cancel()
            if cancelled:
                self._early_reset_to_next_day()
        if cancelled:
            # 17:00 미추첨 취소 → 조기 초기화 → 대시보드 메시지 재생성
            await self.on_reset()
        else:
            await self.on_state_changed()

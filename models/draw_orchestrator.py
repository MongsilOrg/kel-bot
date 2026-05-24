"""추첨 실행 — 우선권 자동 확정 + 랜덤 추첨."""
from __future__ import annotations

import logging
import random
from dataclasses import dataclass
from datetime import date, timedelta

from models.application import Application, ApplicationStatus, ApplicationStore
from models.draw_state import DrawState, DrawStatus
from models.priority import PriorityStore
from utils.time import iso_now

logger = logging.getLogger(__name__)


@dataclass
class DrawResult:
    selected: list[Application]
    rejected: list[Application]
    granted_priority_regions: list[str]  # D+1 우선권 발급된 지역


class DrawOrchestrator:
    """추첨 의사결정·실행. 멱등성 보장."""

    def __init__(
        self,
        applications: ApplicationStore,
        priorities: PriorityStore,
        draw_state: DrawState,
        team_slots: int,
    ) -> None:
        self.applications = applications
        self.priorities = priorities
        self.draw_state = draw_state
        self.team_slots = team_slots

    # 판정 ---------------------------------------------------------------
    def total_active(self) -> int:
        return self.applications.count_active()

    def can_draw_now(self) -> bool:
        if self.draw_state.is_drawn():
            return False
        return self.total_active() >= self.team_slots

    def attempt_primary_draw(self) -> DrawResult | None:
        """00:30 1차 추첨 — 8팀 이상이면 추첨, 미달이면 HELD."""
        if self.draw_state.is_drawn():
            return None
        if self.total_active() >= self.team_slots:
            return self._execute_draw()
        # 미달 — 보류 모드 전환
        if self.draw_state.status != DrawStatus.HELD:
            self.draw_state.status = DrawStatus.HELD
            self.draw_state.save()
        return None

    def attempt_instant_draw(self) -> DrawResult | None:
        """보류(HELD) 상태에서 8팀 도달 시 즉시 추첨.

        00:30 1차 추첨 이전(PENDING)에는 8팀이 차도 추첨하지 않음 — 1차 추첨 시각까지 대기.
        """
        if self.draw_state.status is not DrawStatus.HELD:
            return None
        if self.total_active() >= self.team_slots:
            return self._execute_draw()
        return None

    def force_deadline_cancel(self) -> bool:
        """17:00 데드라인 — 미실행이면 취소 확정, 우선권 소멸."""
        if self.draw_state.deadline_processed:
            return False
        self.draw_state.deadline_processed = True
        if not self.draw_state.is_drawn():
            self.draw_state.status = DrawStatus.CANCELLED
            # 오늘 일자 우선권 모두 소멸 (이월 없음)
            self.priorities.expire_for(self.draw_state.scrim_date)
            self.draw_state.save()
            return True
        self.draw_state.save()
        return False

    # 실행 ---------------------------------------------------------------
    def _execute_draw(self) -> DrawResult:
        scrim_date = self.draw_state.scrim_date
        team_slots = self.team_slots
        active = self.applications.active()

        # 우선권 자동 확정
        priority_regions = self.priorities.regions_for(scrim_date)
        priority_apps = [a for a in active if a.region in priority_regions]
        normal_apps = [a for a in active if a.region not in priority_regions]

        # 우선권 표시 갱신 (had_priority)
        for app in priority_apps:
            app.had_priority = True

        if len(priority_apps) >= team_slots:
            selected = priority_apps[:team_slots]
            extras = priority_apps[team_slots:] + normal_apps
            rejected = extras
        else:
            remaining_slots = team_slots - len(priority_apps)
            random_pool = list(normal_apps)
            random.shuffle(random_pool)
            picked = random_pool[:remaining_slots]
            not_picked = random_pool[remaining_slots:]
            selected = priority_apps + picked
            rejected = not_picked

        self.applications.mark_status((a.team_id for a in selected), ApplicationStatus.SELECTED)
        self.applications.mark_status((a.team_id for a in rejected), ApplicationStatus.REJECTED)

        # 실제 신청·확정된 우선권만 소비 처리
        for region in {a.region for a in priority_apps}:
            self.priorities.consume(region, scrim_date)

        # 다음날(D+1) 우선권 발급 — 탈락 팀, 신청 시각 빠른 순 상위 8
        rejected_sorted = sorted(rejected, key=lambda a: a.applied_at)
        next_date = (date.fromisoformat(scrim_date) + timedelta(days=1)).isoformat()
        granted_regions = [a.region for a in rejected_sorted[:team_slots]]
        if granted_regions:
            self.priorities.grant(granted_regions, next_date, slot_cap=team_slots)

        # 추첨 상태 갱신
        self.draw_state.status = DrawStatus.DONE
        self.draw_state.drawn_at = iso_now()
        self.draw_state.save()

        logger.info(
            "추첨 완료 scrim_date=%s selected=%d rejected=%d 우선권발급=%d",
            scrim_date,
            len(selected),
            len(rejected),
            len(granted_regions),
        )

        return DrawResult(
            selected=selected,
            rejected=rejected,
            granted_priority_regions=granted_regions,
        )

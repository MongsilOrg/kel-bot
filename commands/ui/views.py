"""대시보드/공지/취소 확인 LayoutView."""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import date as date_cls
from typing import Awaitable, Callable, Dict, List, Optional

import discord
from discord import ButtonStyle, Color
from discord.ui import ActionRow, Button, Container, LayoutView, Separator, TextDisplay

from commands.ui.layout_helpers import (
    FOOTER_TEXT,
    error_view,
    info_view,
    success_view,
)
from models.application import Application, ApplicationStatus
from models.draw_state import DrawStatus

_WEEKDAYS = ["월", "화", "수", "목", "금", "토", "일"]

logger = logging.getLogger(__name__)

ApplyHandler = Callable[[discord.Interaction], Awaitable[None]]
CancelHandler = Callable[[discord.Interaction], Awaitable[None]]


# 버튼 쿨다운 ---------------------------------------------------------------
_button_cooldowns: Dict[int, float] = {}
_COOLDOWN_SECONDS = 1.5


def check_cooldown(user_id: int) -> bool:
    """True면 쿨다운 통과(허용), False면 차단."""
    now = time.monotonic()
    last = _button_cooldowns.get(user_id, 0.0)
    if now - last < _COOLDOWN_SECONDS:
        return False
    _button_cooldowns[user_id] = now
    if len(_button_cooldowns) > 200:
        expired = [uid for uid, t in _button_cooldowns.items() if now - t > 60]
        for uid in expired:
            _button_cooldowns.pop(uid, None)
    return True


# 대시보드 ----------------------------------------------------------------
@dataclass
class DashboardSnapshot:
    scrim_date: str
    team_slots: int
    applications: List[Application]
    priority_regions: set[str]
    next_day_priority_regions: set[str]
    draw_status: DrawStatus
    drawn_at: Optional[str]
    deadline_processed: bool
    application_open: bool


def _format_pending_lines(snapshot: DashboardSnapshot) -> str:
    apps = [a for a in snapshot.applications if a.status is ApplicationStatus.PENDING]
    if not apps:
        return "_아직 신청한 팀이 없습니다._"
    lines = []
    for idx, app in enumerate(apps, start=1):
        marker = "★ " if app.region in snapshot.priority_regions else "　 "
        lines.append(f"`{idx:>2}.` {marker}{app.applicant_display}")
    return "\n".join(lines)


def _format_selected_lines(snapshot: DashboardSnapshot) -> str:
    apps = [a for a in snapshot.applications if a.status is ApplicationStatus.SELECTED]
    if not apps:
        return "_없음_"
    lines = []
    for idx, app in enumerate(apps, start=1):
        marker = "★ " if app.had_priority else "　 "
        lines.append(f"`{idx:>2}.` {marker}{app.applicant_display}")
    return "\n".join(lines)


def _format_rejected_lines(snapshot: DashboardSnapshot) -> str:
    apps = [a for a in snapshot.applications if a.status is ApplicationStatus.REJECTED]
    if not apps:
        return "_없음_"
    return "\n".join(f"• {a.applicant_display}" for a in apps)


def _draw_status_label(snapshot: DashboardSnapshot) -> str:
    apps = len(snapshot.applications)
    if snapshot.draw_status is DrawStatus.DONE:
        when = format_kst_short(snapshot.drawn_at)
        return f"✅ 추첨 완료 · {when}" if when else "✅ 추첨 완료"
    if snapshot.draw_status is DrawStatus.CANCELLED:
        if apps == 0:
            return "🌙 오늘 신청 없이 마감"
        return f"❌ 8팀 미달로 취소"
    if snapshot.draw_status is DrawStatus.HELD:
        return "⏸️ 추첨 보류 중"
    if not snapshot.application_open:
        return "🌙 신청 마감"
    return "🟢 신청 접수 중"


def _format_scrim_title(scrim_date: str) -> str:
    try:
        d = date_cls.fromisoformat(scrim_date)
    except ValueError:
        return f"🏆 KEL 스크림 — {scrim_date}"
    weekday = _WEEKDAYS[d.weekday()]
    return f"🏆 {d.month}/{d.day} ({weekday}) KEL 스크림"


def format_kst_short(iso: Optional[str]) -> Optional[str]:
    if not iso:
        return None
    from datetime import datetime
    try:
        dt = datetime.fromisoformat(iso)
    except ValueError:
        return iso
    return dt.strftime("%H:%M")


class DashboardView(LayoutView):
    """영구 대시보드 메시지의 LayoutView.

    버튼 콜백은 외부에서 주입(`apply_handler`, `cancel_handler`).
    """

    def __init__(
        self,
        snapshot: DashboardSnapshot,
        apply_handler: ApplyHandler,
        cancel_handler: CancelHandler,
    ) -> None:
        super().__init__(timeout=None)
        self.snapshot = snapshot
        self.apply_handler = apply_handler
        self.cancel_handler = cancel_handler

        window_closed = not snapshot.application_open
        self.apply_button = Button(
            label="신청",
            style=ButtonStyle.primary,
            emoji="✏️",
            custom_id="kel:apply",
            disabled=window_closed,
        )
        self.apply_button.callback = self._on_apply
        self.cancel_button = Button(
            label="취소",
            style=ButtonStyle.secondary,
            emoji="🗑️",
            custom_id="kel:cancel",
            disabled=window_closed,
        )
        self.cancel_button.callback = self._on_cancel

        title = _format_scrim_title(snapshot.scrim_date)
        status_label = _draw_status_label(snapshot)
        count = f"`{len(snapshot.applications)} / {snapshot.team_slots}`팀"
        header_status = f"{status_label} · {count}"

        is_done = snapshot.draw_status is DrawStatus.DONE

        header_lines = [f"## {title}", header_status]
        if not is_done and snapshot.priority_regions:
            priority_text = ", ".join(sorted(snapshot.priority_regions))
            header_lines.append(f"⭐ 우선권 · {priority_text}")

        children = [
            TextDisplay(content="\n".join(header_lines)),
            Separator(),
        ]

        if is_done:
            selected = _format_selected_lines(snapshot)
            children.append(TextDisplay(content=f"### 선정 8팀\n{selected}"))
            if any(a.status is ApplicationStatus.REJECTED for a in snapshot.applications):
                rejected = _format_rejected_lines(snapshot)
                children.append(TextDisplay(content=f"### 탈락 팀\n{rejected}"))
            if snapshot.next_day_priority_regions:
                next_priority_text = ", ".join(sorted(snapshot.next_day_priority_regions))
                children.append(TextDisplay(content=f"-# 내일 우선권 · {next_priority_text}"))
        else:
            teams = _format_pending_lines(snapshot)
            children.append(TextDisplay(content=f"### 신청 팀\n{teams}"))

        children.append(ActionRow(self.apply_button, self.cancel_button))
        children.append(
            TextDisplay(
                content=(
                    "-# `21:00` 초기화 · `00:30` 추첨 · `17:00` 마감 · "
                    "닉네임 `지역) 이름` 필수"
                )
            )
        )

        self.add_item(Container(*children, accent_colour=Color.green()))

    async def _on_apply(self, interaction: discord.Interaction) -> None:
        if not check_cooldown(interaction.user.id):
            await interaction.response.send_message(
                view=info_view("잠시 후 다시 시도해주세요."),
                ephemeral=True,
            )
            return
        try:
            await self.apply_handler(interaction)
        except Exception:  # noqa: BLE001
            logger.exception("apply_handler 예외")
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    view=error_view("처리 중 오류가 발생했습니다.\n잠시 후 다시 시도해주세요."),
                    ephemeral=True,
                )

    async def _on_cancel(self, interaction: discord.Interaction) -> None:
        if not check_cooldown(interaction.user.id):
            await interaction.response.send_message(
                view=info_view("잠시 후 다시 시도해주세요."),
                ephemeral=True,
            )
            return
        try:
            await self.cancel_handler(interaction)
        except Exception:  # noqa: BLE001
            logger.exception("cancel_handler 예외")
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    view=error_view("처리 중 오류가 발생했습니다.\n잠시 후 다시 시도해주세요."),
                    ephemeral=True,
                )


# 취소 확인 -----------------------------------------------------------------
class CancelConfirmView(LayoutView):
    """취소 확인 LayoutView (ephemeral)."""

    def __init__(
        self,
        region: str,
        on_confirm: Callable[[discord.Interaction], Awaitable[None]],
    ) -> None:
        super().__init__(timeout=60)
        self.region = region
        self.on_confirm = on_confirm

        self.confirm_button = Button(
            label="신청 취소하기",
            style=ButtonStyle.danger,
            emoji="⚠️",
        )
        self.confirm_button.callback = self._confirm
        self.back_button = Button(
            label="돌아가기",
            style=ButtonStyle.secondary,
            emoji="↩️",
        )
        self.back_button.callback = self._back

        container = Container(
            TextDisplay(
                content=(
                    f"## 🚫 신청 취소 확인\n"
                    f"`{region}` 지역 신청을 취소하시겠습니까?"
                )
            ),
            Separator(),
            ActionRow(self.confirm_button, self.back_button),
            TextDisplay(content=FOOTER_TEXT),
            accent_colour=Color.orange(),
        )
        self.add_item(container)

    async def _confirm(self, interaction: discord.Interaction) -> None:
        await self.on_confirm(interaction)

    async def _back(self, interaction: discord.Interaction) -> None:
        await interaction.response.edit_message(
            view=info_view("이전 화면으로 돌아갔습니다."),
        )


# 추첨 결과 공지 ------------------------------------------------------------

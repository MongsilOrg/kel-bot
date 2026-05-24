"""추첨 상태 머신 영속화."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from models.storage import read_json, write_json


class DrawStatus(str, Enum):
    PENDING = "pending"   # 신청 접수 중, 추첨 전
    HELD = "held"         # 1차 추첨 보류 (8팀 미달)
    DONE = "done"         # 추첨 완료
    CANCELLED = "cancelled"  # 17:00 데드라인 도달 후 미달로 취소


@dataclass
class DrawState:
    path: Path
    scrim_date: str
    status: DrawStatus = DrawStatus.PENDING
    drawn_at: str | None = None
    deadline_processed: bool = False

    @classmethod
    def load(cls, path: Path, scrim_date_hint: str) -> "DrawState":
        raw = read_json(path, default=None)
        if raw and raw.get("scrim_date") and raw["scrim_date"] >= scrim_date_hint:
            return cls(
                path=path,
                scrim_date=raw["scrim_date"],
                status=DrawStatus(raw.get("status", "pending")),
                drawn_at=raw.get("drawn_at"),
                deadline_processed=raw.get("deadline_processed", False),
            )
        state = cls(path=path, scrim_date=scrim_date_hint)
        state.save()
        return state

    def save(self) -> None:
        write_json(
            self.path,
            {
                "scrim_date": self.scrim_date,
                "status": self.status.value,
                "drawn_at": self.drawn_at,
                "deadline_processed": self.deadline_processed,
            },
        )

    def reset(self, new_scrim_date: str) -> None:
        self.scrim_date = new_scrim_date
        self.status = DrawStatus.PENDING
        self.drawn_at = None
        self.deadline_processed = False
        self.save()

    def is_drawn(self) -> bool:
        return self.status in (DrawStatus.DONE, DrawStatus.CANCELLED)

    def is_application_closed(self) -> bool:
        """추첨 완료 또는 17:00 데드라인 도달 후 신청 차단."""
        return self.is_drawn()

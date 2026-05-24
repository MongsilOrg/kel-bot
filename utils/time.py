"""KST 시간 헬퍼."""
from __future__ import annotations

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

KST = ZoneInfo("Asia/Seoul")


def now_kst() -> datetime:
    return datetime.now(KST)


def today_kst() -> date:
    return now_kst().date()


def scrim_date_for(moment: datetime, reset_hour: int) -> date:
    """주어진 KST 시각이 속한 스크림 일자(D) 반환.

    reset_hour 이후 시각은 다음 캘린더 날짜를 D로 간주.
    """
    moment_kst = moment.astimezone(KST)
    if moment_kst.hour >= reset_hour:
        return (moment_kst + timedelta(days=1)).date()
    return moment_kst.date()


def current_scrim_date(reset_hour: int) -> date:
    return scrim_date_for(now_kst(), reset_hour)


def kst_at(target_date: date, hour: int, minute: int = 0) -> datetime:
    return datetime.combine(target_date, time(hour=hour, minute=minute), tzinfo=KST)


def format_kst(moment: datetime) -> str:
    return moment.astimezone(KST).strftime("%Y-%m-%d %H:%M:%S KST")


def iso_now() -> str:
    return now_kst().isoformat()

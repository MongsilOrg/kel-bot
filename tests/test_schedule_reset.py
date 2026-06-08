"""리셋 시 대시보드 메시지 재생성 콜백(on_reset) 배선 검증."""
import asyncio

from config.settings import Settings
from models.draw_state import DrawStatus
from models.schedule_manager import ScheduleManager


def _settings(tmp_path):
    return Settings(
        discord_token="x",
        guild_id=None,
        apply_channel_id=1,
        log_channel_id=None,
        reset_hour=21,
        draw_hour=0,
        draw_minute=30,
        deadline_hour=17,
        team_slots=8,
        data_dir=tmp_path,
    )


def _manager(tmp_path, calls):
    def make(name):
        async def _cb(*a, **k):
            calls.append(name)
        return _cb

    return ScheduleManager(
        _settings(tmp_path),
        tmp_path,
        on_draw=make("draw"),
        on_state_changed=make("state"),
        on_deadline_cancelled=make("deadline_cancelled"),
        on_reset=make("reset"),
    )


def test_daily_reset_calls_on_reset(tmp_path):
    calls = []
    mgr = _manager(tmp_path, calls)
    asyncio.run(mgr._run_reset())
    assert "reset" in calls
    assert "state" not in calls  # 일반 갱신이 아니라 재생성 경로


def test_deadline_cancel_calls_on_reset(tmp_path):
    calls = []
    mgr = _manager(tmp_path, calls)
    # PENDING + 미달 상태 → 데드라인에서 취소 → 조기 초기화
    asyncio.run(mgr._run_deadline())
    assert "reset" in calls


def test_deadline_after_draw_does_not_recreate(tmp_path):
    calls = []
    mgr = _manager(tmp_path, calls)
    mgr.state.draw_state.status = DrawStatus.DONE  # 이미 추첨 완료
    asyncio.run(mgr._run_deadline())
    assert "reset" not in calls
    assert "state" in calls

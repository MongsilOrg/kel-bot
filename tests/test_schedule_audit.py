import asyncio

from config.settings import Settings
from models.priority_audit import RemovalEntry
from models.schedule_manager import ScheduleManager


async def _noop(*args, **kwargs):
    pass


def _manager(tmp_path):
    settings = Settings(
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
    return ScheduleManager(
        settings,
        tmp_path,
        on_draw=_noop,
        on_state_changed=_noop,
        on_deadline_cancelled=_noop,
    )


def test_state_bundle_has_audit(tmp_path):
    mgr = _manager(tmp_path)
    assert mgr.state.audit is not None


def test_daily_reset_purges_old_audit(tmp_path):
    mgr = _manager(tmp_path)
    mgr.state.audit.entries.append(
        RemovalEntry(
            region="광주",
            actor_id="1",
            actor_name="홍길동",
            removed_at="2020-01-01T00:00:00+09:00",
            scrim_date="2020-01-01",
            was_self=False,
        )
    )
    asyncio.run(mgr._run_reset())
    assert all(e.scrim_date != "2020-01-01" for e in mgr.state.audit.entries)

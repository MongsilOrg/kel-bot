import asyncio

from commands.dashboard import DashboardController
from config.settings import Settings
from models.schedule_manager import ScheduleManager


async def _noop(*args, **kwargs):
    pass


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


class _Resp:
    def __init__(self):
        self.sent = None
        self.edited = None

    async def send_message(self, *, view=None, ephemeral=False):
        self.sent = {"view": view, "ephemeral": ephemeral}

    async def edit_message(self, *, view=None):
        self.edited = {"view": view}

    def is_done(self):
        return False


class _User:
    def __init__(self, uid, display):
        self.id = uid
        self.display_name = display
        self.name = display


class _Interaction:
    def __init__(self, uid, display):
        self.user = _User(uid, display)
        self.response = _Resp()


def _controller(tmp_path):
    settings = _settings(tmp_path)
    mgr = ScheduleManager(
        settings, tmp_path, on_draw=_noop, on_state_changed=_noop, on_deadline_cancelled=_noop
    )
    ctrl = DashboardController(bot=object(), settings=settings, schedule=mgr)
    ctrl._dashboard_message = None  # refresh no-op
    return ctrl, mgr


def test_confirm_remove_self(tmp_path):
    ctrl, mgr = _controller(tmp_path)
    d = mgr.state.draw_state.scrim_date
    mgr.state.priorities.grant(["광주"], d, slot_cap=8)
    it = _Interaction(1, "광주) 홍길동")
    asyncio.run(ctrl._confirm_remove_priority(it, "광주"))
    assert mgr.state.priorities.regions_for(d) == set()
    entries = mgr.state.audit.entries_for(d)
    assert len(entries) == 1
    assert entries[0].region == "광주"
    assert entries[0].was_self is True


def test_confirm_remove_other(tmp_path):
    ctrl, mgr = _controller(tmp_path)
    d = mgr.state.draw_state.scrim_date
    mgr.state.priorities.grant(["대전"], d, slot_cap=8)
    it = _Interaction(42, "서울) 운영자")
    asyncio.run(ctrl._confirm_remove_priority(it, "대전"))
    assert mgr.state.audit.entries_for(d)[0].was_self is False


def test_handle_remove_no_priority(tmp_path):
    ctrl, mgr = _controller(tmp_path)
    it = _Interaction(1, "광주) 홍길동")
    asyncio.run(ctrl.handle_remove_priority(it))
    assert it.response.sent is not None
    assert it.response.sent["ephemeral"] is True

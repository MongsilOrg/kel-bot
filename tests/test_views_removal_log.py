from commands.ui.views import _format_removal_log_lines
from models.priority_audit import RemovalEntry


def _e(region, at, actor_id="1", action="revoke"):
    return RemovalEntry(
        region=region,
        actor_id=actor_id,
        actor_name="홍길동",
        removed_at=at,
        scrim_date="2026-05-30",
        action=action,
    )


def test_removal_line():
    out = _format_removal_log_lines([_e("광주", "2026-05-30T00:42:00+09:00")])
    assert out == "`00:42` ➖ 광주 <@1>"


def test_grant_line():
    out = _format_removal_log_lines(
        [_e("광주", "2026-05-30T00:42:00+09:00", action="grant")]
    )
    assert out == "`00:42` ➕ 광주 <@1>"


def test_other_removal_line():
    out = _format_removal_log_lines([_e("대전", "2026-05-30T09:15:00+09:00", actor_id="42")])
    assert out == "`09:15` ➖ 대전 <@42>"


def test_multiple_lines_in_order():
    out = _format_removal_log_lines(
        [
            _e("광주", "2026-05-30T00:42:00+09:00", action="grant"),
            _e("대전", "2026-05-30T09:15:00+09:00", actor_id="42"),
        ]
    )
    assert out.splitlines() == ["`00:42` ➕ 광주 <@1>", "`09:15` ➖ 대전 <@42>"]

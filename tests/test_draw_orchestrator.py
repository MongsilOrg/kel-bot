"""추첨 분할 로직 — 두 중대(14·15·16팀) + 일반 추첨(≤13) 검증."""
from models.application import Application, ApplicationStatus, ApplicationStore
from models.draw_state import DrawState
from models.priority import PriorityStore
from models.draw_orchestrator import DrawOrchestrator

SCRIM = "2026-05-30"


def _apps(n):
    return [
        Application(
            team_id=f"t{i}",
            region=f"R{i}",
            applicant_id=f"u{i}",
            applicant_display=f"R{i}) name{i}",
            applied_at=f"2026-05-29T{i:02d}:00:00+09:00",
            scrim_date=SCRIM,
            status=ApplicationStatus.PENDING,
        )
        for i in range(n)
    ]


def _run(tmp_path, n):
    apps = ApplicationStore(path=tmp_path / "a.json", scrim_date=SCRIM, applications=_apps(n))
    pri = PriorityStore.load(tmp_path / "p.json")
    ds = DrawState.load(tmp_path / "d.json", SCRIM)
    return DrawOrchestrator(apps, pri, ds, team_slots=8)._execute_draw()


def _sizes(res):
    a = len(res.groups["A"]) if res.groups else 0
    b = len(res.groups["B"]) if res.groups else 0
    return a, b


def test_15_teams_split_8_7(tmp_path):
    res = _run(tmp_path, 15)
    assert _sizes(res) == (8, 7)               # 1중대 8, 2중대 7
    assert len(res.selected) == 15             # 전원 선정
    assert len(res.rejected) == 0              # 탈락 없음
    assert len(res.granted_priority_regions) == 0  # 우선권 미발급


def test_14_teams_split_7_7(tmp_path):
    res = _run(tmp_path, 14)
    assert _sizes(res) == (7, 7)
    assert len(res.rejected) == 0
    assert len(res.granted_priority_regions) == 0


def test_16_teams_split_8_8(tmp_path):
    res = _run(tmp_path, 16)
    assert _sizes(res) == (8, 8)
    assert len(res.rejected) == 0
    assert len(res.granted_priority_regions) == 0


def test_groups_assigned_on_each_member(tmp_path):
    res = _run(tmp_path, 15)
    assert all(a.group == "A" for a in res.groups["A"])
    assert all(a.group == "B" for a in res.groups["B"])
    # 두 중대 구성원은 서로 겹치지 않음
    ids_a = {a.team_id for a in res.groups["A"]}
    ids_b = {a.team_id for a in res.groups["B"]}
    assert ids_a.isdisjoint(ids_b)


def test_13_teams_single_lottery(tmp_path):
    res = _run(tmp_path, 13)
    assert res.groups is None                  # 두 중대 아님
    assert len(res.selected) == 8
    assert len(res.rejected) == 5
    assert len(res.granted_priority_regions) == 5  # 탈락 → D+1 우선권


def test_8_teams_single_no_reject(tmp_path):
    res = _run(tmp_path, 8)
    assert res.groups is None
    assert len(res.selected) == 8
    assert len(res.rejected) == 0

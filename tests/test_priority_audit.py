from models.priority_audit import PriorityAuditStore, RemovalEntry

DATE = "2026-05-30"


def _entry(region, at, date=DATE, was_self=False):
    return RemovalEntry(
        region=region,
        actor_id="1",
        actor_name="홍길동",
        removed_at=at,
        scrim_date=date,
        was_self=was_self,
    )


def test_record_appends_and_persists(tmp_path):
    path = tmp_path / "audit.json"
    store = PriorityAuditStore.load(path)
    entry = store.record(
        region="광주", actor_id="42", actor_name="운영자", scrim_date=DATE, was_self=False
    )
    assert entry.region == "광주"
    assert [e.region for e in store.entries_for(DATE)] == ["광주"]
    # 영속화 확인
    reloaded = PriorityAuditStore.load(path)
    assert [e.region for e in reloaded.entries_for(DATE)] == ["광주"]


def test_entries_for_filters_by_date(tmp_path):
    store = PriorityAuditStore(
        path=tmp_path / "a.json",
        entries=[_entry("광주", "T1", date=DATE), _entry("부산", "T1", date="2026-05-31")],
    )
    assert [e.region for e in store.entries_for(DATE)] == ["광주"]


def test_entries_for_sorted_by_time(tmp_path):
    store = PriorityAuditStore(
        path=tmp_path / "a.json",
        entries=[
            _entry("부산", "2026-05-30T09:15:00+09:00"),
            _entry("광주", "2026-05-30T00:42:00+09:00"),
        ],
    )
    assert [e.region for e in store.entries_for(DATE)] == ["광주", "부산"]


def test_purge_outdated_drops_old(tmp_path):
    store = PriorityAuditStore(
        path=tmp_path / "a.json",
        entries=[_entry("광주", "T1", date="2026-05-29"), _entry("부산", "T1", date=DATE)],
    )
    store.purge_outdated(DATE)
    assert [e.region for e in store.entries] == ["부산"]


def test_was_self_roundtrip(tmp_path):
    path = tmp_path / "a.json"
    store = PriorityAuditStore.load(path)
    store.record(region="광주", actor_id="1", actor_name="홍길동", scrim_date=DATE, was_self=True)
    reloaded = PriorityAuditStore.load(path)
    assert reloaded.entries_for(DATE)[0].was_self is True

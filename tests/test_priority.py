from models.priority import Priority, PriorityStore

DATE = "2026-05-30"


def _p(region, date=DATE, consumed=False):
    return Priority(
        region=region,
        granted_at="2026-05-29T00:00:00+09:00",
        valid_for_date=date,
        consumed=consumed,
    )


def _store(tmp_path, priorities):
    return PriorityStore(path=tmp_path / "p.json", priorities=priorities)


def test_revoke_removes_active_priority(tmp_path):
    store = _store(tmp_path, [_p("광주"), _p("부산")])
    assert store.revoke("광주", DATE) is True
    assert store.regions_for(DATE) == {"부산"}


def test_revoke_returns_false_when_no_priority(tmp_path):
    store = _store(tmp_path, [_p("부산")])
    assert store.revoke("대구", DATE) is False
    assert store.regions_for(DATE) == {"부산"}


def test_revoke_ignores_consumed(tmp_path):
    store = _store(tmp_path, [_p("광주", consumed=True)])
    assert store.revoke("광주", DATE) is False


def test_revoke_scoped_to_date(tmp_path):
    other = "2026-05-31"
    store = _store(tmp_path, [_p("광주", date=other)])
    assert store.revoke("광주", DATE) is False
    assert store.regions_for(other) == {"광주"}


def test_grant_one_adds_active_priority(tmp_path):
    store = _store(tmp_path, [])
    assert store.grant_one("광주", DATE) is True
    assert store.regions_for(DATE) == {"광주"}


def test_grant_one_rejects_duplicate_active(tmp_path):
    store = _store(tmp_path, [_p("광주")])
    assert store.grant_one("광주", DATE) is False
    assert store.regions_for(DATE) == {"광주"}


def test_grant_one_scoped_to_date(tmp_path):
    other = "2026-05-31"
    store = _store(tmp_path, [_p("광주", date=other)])
    # 다른 날짜엔 활성 우선권이 없으므로 발급 성공
    assert store.grant_one("광주", DATE) is True
    assert store.regions_for(DATE) == {"광주"}
    assert store.regions_for(other) == {"광주"}


def test_grant_one_readds_after_consumed(tmp_path):
    # 이미 소비된 우선권이 있어도 활성으로 재발급 가능
    store = _store(tmp_path, [_p("광주", consumed=True)])
    assert store.grant_one("광주", DATE) is True
    assert store.regions_for(DATE) == {"광주"}

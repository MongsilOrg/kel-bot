"""손상된 JSON 읽기 시 백업 후 기본값 반환 검증."""
from models.storage import read_json


def test_corrupt_json_is_backed_up(tmp_path, caplog):
    path = tmp_path / "state.json"
    path.write_text("{broken", encoding="utf-8")
    assert read_json(path, default={"a": 1}) == {"a": 1}
    backups = list(tmp_path.glob("state.json.corrupt-*"))
    assert len(backups) == 1
    assert backups[0].read_text(encoding="utf-8") == "{broken"
    assert any(r.levelname == "ERROR" for r in caplog.records)

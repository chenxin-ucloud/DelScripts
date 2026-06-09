import pytest
import uuid

from web.app import create_app


@pytest.fixture
def client():
    app, _manager = create_app(testing=True)
    with app.test_client() as c:
        yield c


def test_regions_prod(client):
    resp = client.get("/api/regions?env=prod")
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data, dict)
    # 至少要有一个区域
    assert len(data) >= 1
    # 每条 value 含 Region 和 Zone
    sample = next(iter(data.values()))
    assert "Region" in sample and "Zone" in sample


def test_regions_test(client):
    resp = client.get("/api/regions?env=test")
    assert resp.status_code == 200
    assert len(resp.get_json()) >= 1


def test_regions_invalid_env_defaults_to_prod(client):
    resp = client.get("/api/regions?env=bogus")
    assert resp.status_code == 200


def test_resources_returns_list_of_names(client):
    resp = client.get("/api/resources")
    assert resp.status_code == 200
    names = resp.get_json()
    assert isinstance(names, list)
    assert "UHost" in names
    assert "VPC" in names


def test_snapshot_empty(client):
    resp = client.get("/api/snapshot")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data == {"running": None, "pending": [], "history": []}


def _valid_payload(**overrides):
    base = dict(
        env_name="测试环境",
        public_key="ABC123",
        private_key="secret-xyz",
        project_ids=["org-abc"],
        selected_regions=[],     # 各测试自己填
        selected_resources=["UHost"],
        api_url="",
    )
    base.update(overrides)
    return base


def test_post_task_missing_public_key(client):
    p = _valid_payload(public_key="", selected_regions=["北京"])
    resp = client.post("/api/tasks", json=p)
    assert resp.status_code == 400
    assert resp.get_json()["code"] == "INVALID_PARAM"


def test_post_task_missing_private_key(client):
    p = _valid_payload(private_key="", selected_regions=["北京"])
    resp = client.post("/api/tasks", json=p)
    assert resp.status_code == 400


def test_post_task_empty_project_ids(client):
    p = _valid_payload(project_ids=[], selected_regions=["北京"])
    resp = client.post("/api/tasks", json=p)
    assert resp.status_code == 400


def test_post_task_invalid_env_name(client):
    p = _valid_payload(env_name="开发环境", selected_regions=["北京"])
    resp = client.post("/api/tasks", json=p)
    assert resp.status_code == 400


def test_post_task_unknown_region_rejected(client):
    p = _valid_payload(selected_regions=["平壤"])
    resp = client.post("/api/tasks", json=p)
    assert resp.status_code == 400


def test_post_task_unknown_resource_rejected(client):
    # 拿一个真实存在的区域名
    regions = client.get("/api/regions?env=test").get_json()
    a_region = next(iter(regions.keys()))
    p = _valid_payload(selected_regions=[a_region], selected_resources=["NotAResource"])
    resp = client.post("/api/tasks", json=p)
    assert resp.status_code == 400


def test_post_task_success_returns_task_id_and_position(client):
    regions = client.get("/api/regions?env=test").get_json()
    a_region = next(iter(regions.keys()))
    p = _valid_payload(selected_regions=[a_region])
    resp = client.post("/api/tasks", json=p)
    assert resp.status_code == 200
    data = resp.get_json()
    assert "task_id" in data
    assert data["position"] == 0


def test_get_task_redacts_secrets(client):
    regions = client.get("/api/regions?env=test").get_json()
    a_region = next(iter(regions.keys()))
    p = _valid_payload(public_key="ABCDEFG", selected_regions=[a_region])
    tid = client.post("/api/tasks", json=p).get_json()["task_id"]
    resp = client.get(f"/api/tasks/{tid}")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "private_key" not in data
    assert data["public_key"] == "ABCD***"


def test_get_unknown_task_404(client):
    resp = client.get("/api/tasks/missing")
    assert resp.status_code == 404
    assert resp.get_json()["code"] == "TASK_NOT_FOUND"


def test_stop_unknown_task_404(client):
    resp = client.post("/api/tasks/missing/stop")
    assert resp.status_code == 404


def test_stop_queued_task_succeeds(client):
    regions = client.get("/api/regions?env=test").get_json()
    a_region = next(iter(regions.keys()))
    tid = client.post("/api/tasks", json=_valid_payload(selected_regions=[a_region])).get_json()["task_id"]
    resp = client.post(f"/api/tasks/{tid}/stop")
    assert resp.status_code == 200
    assert resp.get_json()["ok"] is True


def test_stream_unknown_task_404(client):
    resp = client.get("/api/tasks/missing/stream")
    assert resp.status_code == 404


def test_stream_for_terminal_task_emits_state_log_end(client, monkeypatch):
    """构造一个已结束的 task，订阅 stream 应能拿到 state→log→end。"""
    from web.app import create_app
    from web.task_manager import Task
    app, manager = create_app(testing=True)
    t = Task(task_id="done1", state="succeeded")
    t.finished_at = 100.0
    t.append_log({"level": "INFO", "line": "x", "ts": 1.0})
    # 直接塞进 history（绕过队列）
    manager._history.append(t)
    with app.test_client() as c:
        resp = c.get("/api/tasks/done1/stream")
        assert resp.status_code == 200
        body = resp.get_data(as_text=True)
        assert "event: state" in body
        assert "event: log" in body
        assert "event: end" in body
        assert "succeeded" in body

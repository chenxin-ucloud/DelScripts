import pytest

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

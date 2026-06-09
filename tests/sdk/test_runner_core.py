import queue
import threading
import pytest

from sdk import runner_core


class FakeClient:
    def __init__(self, region, project_id):
        self.region = region
        self.project_id = project_id


def fake_get_client(region, project_id, public_key, private_key, base_url=None):
    return FakeClient(region, project_id)


@pytest.fixture
def regions():
    return {
        "北京": {"Region": "cn-bj2", "Zone": "cn-bj2-02"},
        "上海": {"Region": "cn-sh2", "Zone": "cn-sh2-01"},
    }


@pytest.fixture
def captured(monkeypatch):
    calls = []

    def make_op(name):
        def op(client, loc_name, region, zone, project_id, stop_event=None):
            calls.append((name, loc_name, region, project_id))
        return op

    monkeypatch.setattr(runner_core, "DELETE_OPERATIONS", [
        ("UHost", make_op("UHost")),
        ("EIP", make_op("EIP")),
    ])
    monkeypatch.setattr(runner_core, "get_client", fake_get_client)
    return calls


def test_iterates_regions_projects_resources(regions, captured):
    sink = queue.Queue()
    runner_core.run_deletion_core(
        regions=regions,
        project_ids=["proj-A"],
        public_key="pub", private_key="priv", api_url=None,
        selected_regions=["北京", "上海"],
        selected_resources=["UHost", "EIP"],
        log_sink=sink,
        stop_event=threading.Event(),
    )
    assert captured == [
        ("UHost", "北京", "cn-bj2", "proj-A"),
        ("EIP",   "北京", "cn-bj2", "proj-A"),
        ("UHost", "上海", "cn-sh2", "proj-A"),
        ("EIP",   "上海", "cn-sh2", "proj-A"),
    ]


def test_filters_unselected_regions(regions, captured):
    sink = queue.Queue()
    runner_core.run_deletion_core(
        regions=regions,
        project_ids=["proj-A"],
        public_key="p", private_key="p", api_url=None,
        selected_regions=["北京"],         # 只选北京
        selected_resources=["UHost"],
        log_sink=sink,
        stop_event=threading.Event(),
    )
    assert [c[1] for c in captured] == ["北京"]


def test_filters_unselected_resources(regions, captured):
    sink = queue.Queue()
    runner_core.run_deletion_core(
        regions=regions,
        project_ids=["proj-A"],
        public_key="p", private_key="p", api_url=None,
        selected_regions=["北京"],
        selected_resources=["EIP"],        # 只选 EIP
        log_sink=sink,
        stop_event=threading.Event(),
    )
    assert [c[0] for c in captured] == ["EIP"]


def test_stop_event_aborts_outer_loop(regions, monkeypatch):
    stop_event = threading.Event()
    calls = []

    def op(client, loc_name, region, zone, project_id, stop_event=None):
        calls.append(loc_name)
        stop_event.set()  # 第一个调用后立刻停

    monkeypatch.setattr(runner_core, "DELETE_OPERATIONS", [("UHost", op)])
    monkeypatch.setattr(runner_core, "get_client", fake_get_client)

    sink = queue.Queue()
    runner_core.run_deletion_core(
        regions=regions,
        project_ids=["proj-A", "proj-B"],
        public_key="p", private_key="p", api_url=None,
        selected_regions=["北京", "上海"],
        selected_resources=["UHost"],
        log_sink=sink,
        stop_event=stop_event,
    )
    assert calls == ["北京"]   # 上海不会被处理


def test_log_sink_receives_structured_dict(regions, captured):
    sink = queue.Queue()
    runner_core.run_deletion_core(
        regions=regions,
        project_ids=["proj-A"],
        public_key="p", private_key="p", api_url=None,
        selected_regions=["北京"],
        selected_resources=["UHost"],
        log_sink=sink,
        stop_event=threading.Event(),
    )
    items = []
    while not sink.empty():
        items.append(sink.get_nowait())
    # 至少要发出一条「处理区域: 北京」类的 INFO
    assert any(
        isinstance(it, dict) and it.get("level") == "INFO" and "北京" in it.get("line", "")
        for it in items
    )

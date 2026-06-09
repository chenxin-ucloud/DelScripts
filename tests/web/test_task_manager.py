import time
import threading
import pytest

from web.task_manager import Task, TaskManager


@pytest.fixture
def manager():
    """构造一个 worker 不自启的 TaskManager 以便单测队列逻辑。"""
    m = TaskManager(autostart=False)
    yield m


def _make_task(task_id="t1", **kw):
    return Task(task_id=task_id, **kw)


def test_submit_first_task_returns_position_0(manager):
    t = _make_task()
    pos = manager.submit(t)
    assert pos == 0


def test_submit_second_task_returns_position_1(manager):
    manager.submit(_make_task("t1"))
    pos = manager.submit(_make_task("t2"))
    assert pos == 1


def test_get_returns_pending_task(manager):
    t = _make_task("abc")
    manager.submit(t)
    assert manager.get("abc") is t


def test_get_unknown_returns_none(manager):
    assert manager.get("missing") is None


def test_snapshot_lists_pending(manager):
    manager.submit(_make_task("t1"))
    manager.submit(_make_task("t2"))
    snap = manager.snapshot()
    assert snap["running"] is None
    assert [t["task_id"] for t in snap["pending"]] == ["t1", "t2"]
    assert snap["history"] == []


def test_snapshot_redacts_secrets(manager):
    manager.submit(_make_task("t1", public_key="ABCDEFG", private_key="secret"))
    snap = manager.snapshot()
    pending = snap["pending"][0]
    assert "private_key" not in pending
    assert pending["public_key"] == "ABCD***"


def test_stop_queued_task_removes_from_pending(manager):
    manager.submit(_make_task("t1"))
    manager.submit(_make_task("t2"))
    ok = manager.stop("t1")
    assert ok
    assert [t["task_id"] for t in manager.snapshot()["pending"]] == ["t2"]


def test_stop_unknown_returns_false(manager):
    assert manager.stop("missing") is False


def test_stop_running_sets_stop_event(manager):
    # 模拟 worker 已开始执行
    t = _make_task("t1")
    manager._pending.append(t)
    manager._move_to_running(t)  # 测试用辅助
    assert not t.stop_event.is_set()
    ok = manager.stop("t1")
    assert ok
    assert t.stop_event.is_set()


def test_position_of_pending(manager):
    t1 = _make_task("t1"); t2 = _make_task("t2"); t3 = _make_task("t3")
    for t in [t1, t2, t3]:
        manager.submit(t)
    assert manager.position_of(t1) == 0
    assert manager.position_of(t2) == 1
    assert manager.position_of(t3) == 2


def test_position_of_running_is_zero(manager):
    t = _make_task("t1")
    manager._pending.append(t)
    manager._move_to_running(t)
    assert manager.position_of(t) == 0

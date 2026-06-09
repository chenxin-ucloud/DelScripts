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


def test_worker_runs_task_to_succeeded(monkeypatch):
    """worker 调用 run_deletion_core 后任务进 succeeded，私钥被擦除。"""
    from web import task_manager as tm

    called = {}

    def fake_runner(**kw):
        called["kw"] = kw
        kw["log_sink"].put({"level": "INFO", "line": "fake done", "ts": 0.0})

    monkeypatch.setattr(tm, "run_deletion_core", fake_runner)
    # 也要 stub 区域加载
    monkeypatch.setattr(tm, "_load_regions_for_env", lambda env: {"北京": {"Region":"cn-bj2","Zone":"cn-bj2-02"}})

    manager = tm.TaskManager(autostart=True)
    t = tm.Task(
        task_id="t1", env_name="测试环境",
        public_key="pub", private_key="SECRET",
        project_ids=["p1"], selected_regions=["北京"],
        selected_resources=["UHost"],
    )
    manager.submit(t)
    # 等任务跑完
    for _ in range(50):
        if t.state in ("succeeded", "failed", "stopped"):
            break
        time.sleep(0.05)
    assert t.state == "succeeded"
    assert t.private_key == ""           # 私钥已擦除
    assert t.finished_at is not None
    # log_sink 收到了日志
    lines = [it["line"] for it in t.log_buffer]
    assert "fake done" in lines


def test_worker_handles_runner_exception_as_failed(monkeypatch):
    from web import task_manager as tm

    def boom(**kw):
        raise RuntimeError("boom")

    monkeypatch.setattr(tm, "run_deletion_core", boom)
    monkeypatch.setattr(tm, "_load_regions_for_env", lambda env: {"北京": {"Region":"cn-bj2","Zone":"cn-bj2-02"}})

    manager = tm.TaskManager(autostart=True)
    t = tm.Task(task_id="t2", env_name="测试环境",
                public_key="p", private_key="p",
                project_ids=["p1"], selected_regions=["北京"], selected_resources=["UHost"])
    manager.submit(t)
    for _ in range(50):
        if t.state in ("succeeded","failed","stopped"):
            break
        time.sleep(0.05)
    assert t.state == "failed"
    assert t.private_key == ""


def test_worker_serializes_two_tasks(monkeypatch):
    """两个任务依次执行，第二个的 started_at 晚于第一个的 finished_at。"""
    from web import task_manager as tm

    def slow(**kw):
        time.sleep(0.2)

    monkeypatch.setattr(tm, "run_deletion_core", slow)
    monkeypatch.setattr(tm, "_load_regions_for_env", lambda env: {"北京": {"Region":"cn-bj2","Zone":"cn-bj2-02"}})

    manager = tm.TaskManager(autostart=True)
    t1 = tm.Task(task_id="t1", env_name="测试环境", public_key="p", private_key="p",
                 project_ids=["p"], selected_regions=["北京"], selected_resources=["UHost"])
    t2 = tm.Task(task_id="t2", env_name="测试环境", public_key="p", private_key="p",
                 project_ids=["p"], selected_regions=["北京"], selected_resources=["UHost"])
    manager.submit(t1)
    manager.submit(t2)
    for _ in range(100):
        if t1.state == "succeeded" and t2.state == "succeeded":
            break
        time.sleep(0.05)
    assert t1.state == "succeeded" and t2.state == "succeeded"
    assert t2.started_at >= t1.finished_at


def test_worker_bridges_sdk_logger_into_task_buffer(monkeypatch):
    """SDK 内部 logger.info()/error() 应桥接到 task.log_buffer。"""
    import logging
    from web import task_manager as tm

    def fake_runner(**kw):
        # 模拟 SDK 内部 delete_* 通过自己的 logger 输出（包括错误）
        sdk_logger = logging.getLogger("sdk.delete_all_resources")
        sdk_logger.info("处理资源 X")
        sdk_logger.error("删除 X 失败: 230 Params [Region] not available")

    monkeypatch.setattr(tm, "run_deletion_core", fake_runner)
    monkeypatch.setattr(tm, "_load_regions_for_env",
                        lambda env: {"北京": {"Region": "cn-bj2", "Zone": "cn-bj2-02"}})

    manager = tm.TaskManager(autostart=True)
    t = tm.Task(task_id="bridge1", env_name="测试环境",
                public_key="p", private_key="p",
                project_ids=["p1"], selected_regions=["北京"], selected_resources=["UHost"])
    manager.submit(t)
    for _ in range(50):
        if t.state in ("succeeded", "failed", "stopped"):
            break
        time.sleep(0.05)
    assert t.state == "succeeded"
    lines = [it["line"] for it in t.log_buffer]
    assert "处理资源 X" in lines
    assert any("Params [Region] not available" in line for line in lines)
    # 同时确认 ERROR level 被保留
    levels = [it["level"] for it in t.log_buffer]
    assert "ERROR" in levels


def test_worker_removes_bridge_handler_between_tasks(monkeypatch):
    """每个任务完成后桥接 handler 必须移除，避免下个任务收到上个任务的遗留日志。"""
    import logging
    from web import task_manager as tm

    def fake_runner(**kw):
        logging.getLogger("sdk.delete_all_resources").info("task log")

    monkeypatch.setattr(tm, "run_deletion_core", fake_runner)
    monkeypatch.setattr(tm, "_load_regions_for_env",
                        lambda env: {"北京": {"Region": "cn-bj2", "Zone": "cn-bj2-02"}})

    manager = tm.TaskManager(autostart=True)
    t1 = tm.Task(task_id="iso1", env_name="测试环境", public_key="p", private_key="p",
                 project_ids=["p"], selected_regions=["北京"], selected_resources=["UHost"])
    manager.submit(t1)
    for _ in range(50):
        if t1.state == "succeeded":
            break
        time.sleep(0.05)

    sdk_logger = logging.getLogger("sdk.delete_all_resources")
    handlers_after = [h for h in sdk_logger.handlers if isinstance(h, __import__("web.log_handler", fromlist=["BufferHandler"]).BufferHandler)]
    assert handlers_after == [], "bridge handler 未在任务结束后移除"

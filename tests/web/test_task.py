import threading
import pytest

from web.task_manager import Task


def test_default_state_is_queued():
    t = Task(task_id="abc", env_name="测试环境")
    assert t.state == "queued"
    assert t.started_at is None
    assert t.finished_at is None
    assert t.subscribers == 0


def test_append_log_adds_to_buffer():
    t = Task(task_id="abc")
    t.append_log({"level": "INFO", "line": "x", "ts": 1.0})
    t.append_log({"level": "ERROR", "line": "y", "ts": 2.0})
    assert list(t.log_buffer) == [
        {"level": "INFO", "line": "x", "ts": 1.0},
        {"level": "ERROR", "line": "y", "ts": 2.0},
    ]


def test_put_is_alias_for_append_log():
    t = Task(task_id="abc")
    t.put({"level": "INFO", "line": "hello", "ts": 0.0})
    assert list(t.log_buffer) == [{"level": "INFO", "line": "hello", "ts": 0.0}]


def test_append_log_notifies_cond():
    t = Task(task_id="abc")
    notified = threading.Event()

    def waiter():
        with t.log_cond:
            t.log_cond.wait(timeout=2.0)
        notified.set()

    th = threading.Thread(target=waiter, daemon=True)
    th.start()
    # 确保 waiter 已进入 wait
    import time; time.sleep(0.05)

    t.append_log({"level": "INFO", "line": "ping", "ts": 0.0})
    assert notified.wait(timeout=1.0)


def test_log_buffer_caps_at_500():
    t = Task(task_id="abc")
    for i in range(600):
        t.append_log({"level": "INFO", "line": f"line{i}", "ts": 0.0})
    assert len(t.log_buffer) == 500
    assert t.log_buffer[0]["line"] == "line100"
    assert t.log_buffer[-1]["line"] == "line599"


def test_to_public_dict_redacts_secrets():
    t = Task(task_id="abc", public_key="4Z7T2qoQv6HA30J1chPHKBFKdaLRu15RJ",
             private_key="secret-private", env_name="测试环境")
    pub = t.to_public_dict()
    assert "private_key" not in pub
    assert pub["public_key"] == "4Z7T***"
    assert pub["task_id"] == "abc"
    assert pub["env_name"] == "测试环境"


def test_to_public_dict_empty_public_key():
    t = Task(task_id="abc", public_key="")
    pub = t.to_public_dict()
    assert pub["public_key"] == ""

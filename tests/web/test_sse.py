import threading
import time
import pytest

from web.task_manager import Task
from web.sse import format_event, stream_events


def test_format_event_basic():
    out = format_event("log", {"level": "INFO", "line": "hi"})
    assert out.startswith("event: log\n")
    assert "data: " in out
    assert out.endswith("\n\n")


def test_stream_events_replays_buffer_then_ends_on_terminal_state():
    task = Task(task_id="t1", state="succeeded")
    task.finished_at = 12345.0
    task.append_log({"level": "INFO", "line": "step 1", "ts": 1.0})
    task.append_log({"level": "INFO", "line": "step 2", "ts": 2.0})

    events = list(stream_events(task, max_idle_seconds=0.1))
    blob = "".join(events)
    # 首帧 state
    assert "event: state" in blob
    # 重放两条日志
    assert "step 1" in blob and "step 2" in blob
    # 终态 end 事件
    assert "event: end" in blob
    assert "succeeded" in blob


def test_stream_events_streams_new_logs_then_terminal():
    """运行中任务：先 replay buffer，然后推增量，最后终态结束。"""
    task = Task(task_id="t1", state="running")
    task.append_log({"level": "INFO", "line": "initial", "ts": 0.0})

    def feeder():
        time.sleep(0.05)
        task.append_log({"level": "INFO", "line": "second", "ts": 1.0})
        time.sleep(0.05)
        task.state = "succeeded"
        task.finished_at = 99.0
        with task.log_cond:
            task.log_cond.notify_all()

    th = threading.Thread(target=feeder, daemon=True)
    th.start()
    events = list(stream_events(task, max_idle_seconds=1.0))
    th.join(timeout=1.0)

    blob = "".join(events)
    assert "initial" in blob
    assert "second" in blob
    assert "event: end" in blob


def test_stream_events_404_helper():
    """sentinel: stream_events 假定 task 不为 None；调用方负责 404。
    本测试只是文档化该契约——直接传 None 应抛 AttributeError，提醒调用方校验。"""
    with pytest.raises(AttributeError):
        list(stream_events(None, max_idle_seconds=0.1))

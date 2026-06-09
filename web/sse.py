"""SSE 事件序列化与 stream_events 生成器（独立于 Flask 以便单测）。"""
import json
import time
from typing import Iterator

TERMINAL_STATES = {"succeeded", "failed", "stopped"}


def format_event(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def stream_events(task, max_idle_seconds: float = 15.0) -> Iterator[str]:
    """生成 SSE 字符串流。

    协议：
    1. 首帧：state 事件（含当前状态）
    2. 重放 log_buffer 内所有日志
    3. 循环 cond.wait，唤醒后推增量 log 事件；空闲超时发 heartbeat
    4. 任务进入终态后，发最终 state + end，停止迭代

    Args:
        task: Task 对象（调用方负责非 None 校验）
        max_idle_seconds: 多久无新事件发一次 heartbeat
    """
    task.subscribers += 1
    try:
        # 1) 首帧
        state_payload = {"state": task.state}
        if task.started_at is not None:
            state_payload["started_at"] = task.started_at
        if task.finished_at is not None:
            state_payload["finished_at"] = task.finished_at
        yield format_event("state", state_payload)

        # 2) 重放当前 buffer
        with task.log_cond:
            snapshot = list(task.log_buffer)
            last_index = len(task.log_buffer)
        for item in snapshot:
            yield format_event("log", item)

        # 终态：直接结束
        if task.state in TERMINAL_STATES:
            yield format_event("state", {
                "state": task.state,
                "finished_at": task.finished_at,
            })
            yield format_event("end", {"terminal": task.state})
            return

        # 3) 增量推送
        last_heartbeat = time.monotonic()
        while True:
            with task.log_cond:
                # 等待新日志或终态
                if last_index == len(task.log_buffer) and task.state not in TERMINAL_STATES:
                    task.log_cond.wait(timeout=max_idle_seconds)
                new_items = list(task.log_buffer)[last_index:]
                last_index = len(task.log_buffer)
                current_state = task.state
            for it in new_items:
                yield format_event("log", it)
            if current_state in TERMINAL_STATES:
                yield format_event("state", {
                    "state": current_state,
                    "finished_at": task.finished_at,
                })
                yield format_event("end", {"terminal": current_state})
                return
            # heartbeat
            if not new_items and (time.monotonic() - last_heartbeat) >= max_idle_seconds:
                yield format_event("heartbeat", {})
                last_heartbeat = time.monotonic()
    finally:
        task.subscribers = max(0, task.subscribers - 1)

"""Task 数据模型与 TaskManager 队列管理。"""
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from typing import List, Optional


def _redact_public_key(pk: str) -> str:
    if not pk:
        return ""
    if len(pk) <= 4:
        return pk + "***"
    return pk[:4] + "***"


@dataclass
class Task:
    task_id: str
    state: str = "queued"
    submitted_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    finished_at: Optional[float] = None
    env_name: str = "正式环境"
    api_url: str = ""
    project_ids: List[str] = field(default_factory=list)
    selected_regions: List[str] = field(default_factory=list)
    selected_resources: List[str] = field(default_factory=list)
    public_key: str = ""
    private_key: str = ""  # 进终态后由 TaskManager 立刻置空
    log_buffer: deque = field(default_factory=lambda: deque(maxlen=500))
    log_cond: threading.Condition = field(default_factory=threading.Condition)
    stop_event: threading.Event = field(default_factory=threading.Event)
    subscribers: int = 0

    def append_log(self, item: dict) -> None:
        with self.log_cond:
            self.log_buffer.append(item)
            self.log_cond.notify_all()

    # log_sink 接口别名
    def put(self, item: dict) -> None:
        self.append_log(item)

    def to_public_dict(self) -> dict:
        """脱敏视图：不含 private_key，public_key 截断。"""
        return {
            "task_id": self.task_id,
            "state": self.state,
            "submitted_at": self.submitted_at,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "env_name": self.env_name,
            "api_url": self.api_url,
            "project_ids": list(self.project_ids),
            "selected_regions": list(self.selected_regions),
            "selected_resources": list(self.selected_resources),
            "public_key": _redact_public_key(self.public_key),
        }


# TaskManager 在 Task 7 添加

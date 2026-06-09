"""把 Python logging 的 LogRecord 转换为结构化 dict 推到 log sink。"""
import logging
import time


class BufferHandler(logging.Handler):
    """把 LogRecord 转成 {"level","line","ts"} 推到 sink.put()"""

    def __init__(self, sink):
        super().__init__()
        self.sink = sink

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self.sink.put({
                "level": record.levelname,
                "line": record.getMessage(),
                "ts": time.time(),
            })
        except Exception:
            # 与标准库一致：handler 异常不传播
            self.handleError(record)

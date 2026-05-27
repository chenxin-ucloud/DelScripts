import logging
import queue


class QueueHandler(logging.Handler):
    """将日志记录放入 queue，供 GUI 主线程轮询显示"""

    def __init__(self, log_queue: queue.Queue):
        super().__init__()
        self.log_queue = log_queue

    def emit(self, record: logging.LogRecord):
        self.log_queue.put(self.format(record))

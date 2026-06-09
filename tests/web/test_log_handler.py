import logging
import pytest

from web.log_handler import BufferHandler


class FakeSink:
    def __init__(self):
        self.items = []

    def put(self, item):
        self.items.append(item)


def test_emit_pushes_structured_dict():
    sink = FakeSink()
    handler = BufferHandler(sink)
    logger = logging.getLogger("test.buffer.handler")
    logger.handlers.clear()
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    logger.info("hello %s", "world")
    logger.error("oops")

    assert len(sink.items) == 2
    assert sink.items[0]["level"] == "INFO"
    assert sink.items[0]["line"] == "hello world"
    assert "ts" in sink.items[0]
    assert sink.items[1]["level"] == "ERROR"
    assert sink.items[1]["line"] == "oops"


def test_emit_swallows_failures(monkeypatch):
    """logging handler 不应让异常逃出，否则会污染 logger 调用方"""
    class BrokenSink:
        def put(self, item):
            raise RuntimeError("disk full")

    handler = BufferHandler(BrokenSink())
    logger = logging.getLogger("test.buffer.broken")
    logger.handlers.clear()
    logger.addHandler(handler)
    # 不该抛出
    logger.info("noop")

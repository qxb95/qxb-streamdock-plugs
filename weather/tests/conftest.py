import json
import logging
import os
import sys
import tempfile

import pytest

PLUGIN_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PLUGIN_ROOT not in sys.path:
    sys.path.insert(0, PLUGIN_ROOT)

# 单元测试期间把日志文件写入临时目录，避免污染仓库中的 logs/ 目录。
_LOG_DIR = tempfile.mkdtemp(prefix='streamdock-tests-logs-')
_RealFileHandler = logging.FileHandler


class _TempDirFileHandler(_RealFileHandler):
    def __init__(self, filename, *args, **kwargs):
        super().__init__(os.path.join(_LOG_DIR, os.path.basename(filename)), *args, **kwargs)


logging.FileHandler = _TempDirFileHandler


class FakeWebSocket:
    """记录所有发送内容的 WebSocket 替身。"""

    def __init__(self):
        self.sent = []
        self.closed = False

    def send(self, message):
        self.sent.append(message)

    def close(self):
        self.closed = True

    @property
    def events(self):
        return [json.loads(m) for m in self.sent]

    def events_of(self, event):
        return [e for e in self.events if e.get('event') == event]

    def last_event(self):
        return self.events[-1]


class FakeTimer:
    """不启动线程的 Timer 替身，只记录注册的定时器。"""

    def __init__(self):
        self.intervals = {}
        self.cleared = []

    def set_interval(self, uuid, delay, callback):
        self.intervals[uuid] = {'delay': delay, 'callback': callback}

    def clear_interval(self, uuid):
        self.cleared.append(uuid)
        self.intervals.pop(uuid, None)


class FakePlugin:
    def __init__(self, ws=None):
        self.ws = FakeWebSocket() if ws is None else ws
        self.timer = FakeTimer()
        self.actions = {}
        self.global_settings = None
        self.plugin_uuid = 'plugin-uuid'
        self.global_settings_calls = []

    def set_global_settings(self, payload):
        self.global_settings_calls.append(payload)
        self.global_settings = payload


@pytest.fixture
def ws():
    return FakeWebSocket()


@pytest.fixture
def plugin(ws):
    return FakePlugin(ws)

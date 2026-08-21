"""各插件测试共用的替身：WebSocket、Timer、Plugin，以及日志重定向。"""

import json
import logging
import os
import tempfile

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def redirect_log_files():
    """把 logging.FileHandler 的输出重定向到临时目录，避免测试污染仓库的 logs/。"""
    log_dir = tempfile.mkdtemp(prefix='streamdock-tests-logs-')
    real_file_handler = logging.FileHandler

    if getattr(real_file_handler, '_streamdock_redirected', False):
        return

    class _TempDirFileHandler(real_file_handler):
        _streamdock_redirected = True

        def __init__(self, filename, *args, **kwargs):
            super().__init__(os.path.join(log_dir, os.path.basename(filename)), *args, **kwargs)

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
    """Plugin 替身，不建立 WebSocket 连接也不启动定时器线程。"""

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

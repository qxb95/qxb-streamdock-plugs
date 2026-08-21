"""music_display 插件的测试配置。

该插件依赖仅存在于 Windows 的 pycaw / winrt，因此在导入被测模块之前
先注入替身模块，使测试可以在任意平台运行。
"""

import json
import logging
import os
import sys
import tempfile
import types

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


class FakeAudioUtilities:
    """pycaw.AudioUtilities 替身，会话状态由测试设置。"""

    sessions = []
    raises = None

    @classmethod
    def GetAllSessions(cls):
        if cls.raises is not None:
            raise cls.raises
        return cls.sessions

    @classmethod
    def reset(cls):
        cls.sessions = []
        cls.raises = None


class FakeMediaManager:
    """winrt GlobalSystemMediaTransportControlsSessionManager 替身。"""

    session = None
    raises = None

    @classmethod
    async def request_async(cls):
        if cls.raises is not None:
            raise cls.raises
        return cls

    @classmethod
    def get_current_session(cls):
        return cls.session

    @classmethod
    def reset(cls):
        cls.session = None
        cls.raises = None


def _install_windows_stubs():
    pycaw_pkg = types.ModuleType('pycaw')
    pycaw_mod = types.ModuleType('pycaw.pycaw')
    pycaw_mod.AudioUtilities = FakeAudioUtilities
    pycaw_pkg.pycaw = pycaw_mod

    winrt = types.ModuleType('winrt')
    windows = types.ModuleType('winrt.windows')
    media = types.ModuleType('winrt.windows.media')
    control = types.ModuleType('winrt.windows.media.control')
    control.GlobalSystemMediaTransportControlsSessionManager = FakeMediaManager
    winrt.windows = windows
    windows.media = media
    media.control = control

    sys.modules.setdefault('pycaw', pycaw_pkg)
    sys.modules.setdefault('pycaw.pycaw', pycaw_mod)
    sys.modules.setdefault('winrt', winrt)
    sys.modules.setdefault('winrt.windows', windows)
    sys.modules.setdefault('winrt.windows.media', media)
    sys.modules.setdefault('winrt.windows.media.control', control)


_install_windows_stubs()


class FakeWebSocket:
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


@pytest.fixture(autouse=True)
def reset_windows_stubs():
    FakeAudioUtilities.reset()
    FakeMediaManager.reset()
    yield
    FakeAudioUtilities.reset()
    FakeMediaManager.reset()


@pytest.fixture
def ws():
    return FakeWebSocket()


@pytest.fixture
def plugin(ws):
    return FakePlugin(ws)

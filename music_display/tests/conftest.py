"""music_display 插件的测试配置。

该插件依赖仅存在于 Windows 的 pycaw / winrt，因此在导入被测模块之前
先注入替身模块，使测试可以在任意平台运行。
"""

import os
import sys
import types

import pytest

PLUGIN_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO_ROOT = os.path.dirname(PLUGIN_ROOT)
for _path in (REPO_ROOT, PLUGIN_ROOT):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from tests.fakes import FakePlugin, FakeWebSocket, redirect_log_files  # noqa: E402

redirect_log_files()


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


@pytest.fixture(autouse=True)
def plugin_dir_as_app_dir(monkeypatch):
    """让 streamdock_core.paths 把插件目录当作运行目录，从而找到插件自带资源。"""
    monkeypatch.setattr('streamdock_core.paths.app_dir', lambda: PLUGIN_ROOT)
    monkeypatch.setattr('streamdock_core.paths.bundle_dir', lambda: PLUGIN_ROOT)

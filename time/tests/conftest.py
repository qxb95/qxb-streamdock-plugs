"""time 插件的测试配置。"""
import os
import sys

import pytest

PLUGIN_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO_ROOT = os.path.dirname(PLUGIN_ROOT)
for _path in (REPO_ROOT, PLUGIN_ROOT):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from tests.fakes import FakePlugin, FakeWebSocket, redirect_log_files  # noqa: E402

redirect_log_files()


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

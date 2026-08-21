import json
import threading
import time

import pytest

from streamdock_core import app

#: 记录 scan_and_register_actions 收到的 actions 目录
scanned = []

ARGV = [
    'plugin.py',
    '-port', '28196',
    '-pluginUUID', 'uuid-1',
    '-registerEvent', 'registerPlugin',
    '-info', '{"application": {}}',
]


class FakeWs:
    def __init__(self, on_close=None):
        self.on_close = on_close


class FakePlugin:
    """记录构造参数，并在 run_plugin 注册好 on_close 后触发关闭。"""

    created = []

    def __init__(self, port, plugin_uuid, event, info, on_close=None):
        self.port = port
        self.plugin_uuid = plugin_uuid
        self.event = event
        self.info = info
        self.ws = FakeWs(on_close)
        self.stopped = False
        self._original_on_close = on_close
        FakePlugin.created.append(self)
        threading.Thread(target=self._close_when_ready, daemon=True).start()

    def _close_when_ready(self):
        deadline = time.time() + 5
        while time.time() < deadline:
            if self.ws.on_close is not self._original_on_close:
                self.ws.on_close(self.ws, 1000, 'bye')
                return
            time.sleep(0.01)

    def stop(self):
        self.stopped = True


@pytest.fixture(autouse=True)
def fast_startup(monkeypatch):
    FakePlugin.created = []
    scanned.clear()
    monkeypatch.setattr(app, 'STARTUP_DELAY', 0)
    monkeypatch.setattr(app.ActionFactory, 'scan_and_register_actions', classmethod(
        lambda cls, actions_dir=None: scanned.append(actions_dir)))


def test_parse_args_reads_streamdock_arguments(monkeypatch):
    monkeypatch.setattr(app.sys, 'argv', ARGV)

    args = app.parse_args('time')

    assert args.port == 28196
    assert args.pluginUUID == 'uuid-1'
    assert args.registerEvent == 'registerPlugin'
    assert json.loads(args.info) == {'application': {}}


def test_parse_args_requires_all_arguments(monkeypatch):
    monkeypatch.setattr(app.sys, 'argv', ['plugin.py', '-port', '1'])

    with pytest.raises(SystemExit):
        app.parse_args('time')


def test_run_plugin_scans_actions_and_starts_plugin(monkeypatch):
    monkeypatch.setattr(app.sys, 'argv', ARGV)
    monkeypatch.setattr(app, 'Plugin', FakePlugin)

    app.run_plugin('time', actions_dir='/tmp/actions')

    plugin = FakePlugin.created[0]
    assert scanned == ['/tmp/actions']
    assert (plugin.port, plugin.plugin_uuid, plugin.event) == (28196, 'uuid-1', 'registerPlugin')


def test_run_plugin_returns_after_websocket_close(monkeypatch):
    monkeypatch.setattr(app.sys, 'argv', ARGV)
    monkeypatch.setattr(app, 'Plugin', FakePlugin)

    app.run_plugin('time')

    assert scanned == [None]
    assert FakePlugin.created[0].stopped is True


def test_run_plugin_keeps_original_on_close_callback(monkeypatch):
    calls = []
    monkeypatch.setattr(app.sys, 'argv', ARGV)
    monkeypatch.setattr(
        app, 'Plugin',
        lambda *a: FakePlugin(*a, on_close=lambda ws, code, msg: calls.append((code, msg))),
    )

    app.run_plugin('time')

    assert calls == [(1000, 'bye')]


def test_run_plugin_exits_with_code_1_on_failure(monkeypatch):
    monkeypatch.setattr(app.sys, 'argv', ARGV)

    def boom(*args, **kwargs):
        raise RuntimeError('boom')

    monkeypatch.setattr(app, 'Plugin', boom)

    with pytest.raises(SystemExit) as excinfo:
        app.run_plugin('time')

    assert excinfo.value.code == 1

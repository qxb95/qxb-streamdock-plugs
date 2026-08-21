import json

import pytest

from streamdock_core.action import Action
from streamdock_core.plugin import CONTEXT_EVENTS, GLOBAL_EVENTS, Plugin

from tests.fakes import FakePlugin, FakeTimer, FakeWebSocket

HOOKS = sorted(
    {name for name, _ in CONTEXT_EVENTS.values()}
    | set(GLOBAL_EVENTS.values())
    | {'on_will_appear', 'on_will_disappear', 'on_did_receive_global_settings'}
)


class RecordingAction(Action):
    """覆盖所有生命周期回调并记录调用的 Action 子类。"""

    def __init__(self, action='com.qxb.time.time', context='ctx'):
        super().__init__(action, context, {}, FakePlugin())
        self.calls = []


def _recorder(name):
    def handler(self, *args):
        self.calls.append((name, args))

    return handler


for _hook in HOOKS:
    setattr(RecordingAction, _hook, _recorder(_hook))


class BareAction(Action):
    """未覆盖任何回调的 Action 子类，用于验证基类默认实现。"""

    def __init__(self, action='com.qxb.time.time', context='ctx'):
        super().__init__(action, context, {}, FakePlugin())


@pytest.fixture
def instance():
    """跳过 __init__（会建立真实 WebSocket 连接）构造 Plugin。"""
    plugin = Plugin.__new__(Plugin)
    plugin.actions = {}
    plugin.global_settings = None
    plugin.timer = FakeTimer()
    plugin.plugin_uuid = 'plugin-uuid'
    plugin._connected = True
    plugin.ws = FakeWebSocket()
    return plugin


def send(plugin, **data):
    plugin._on_message(plugin.ws, json.dumps(data))


def test_on_open_registers_plugin(instance):
    instance._connected = False

    instance._on_open(instance.ws, 'registerPlugin', 'uuid-1')

    assert instance._connected is True
    assert instance.ws.last_event() == {'event': 'registerPlugin', 'uuid': 'uuid-1'}


def test_on_error_and_on_close_mark_disconnected(instance):
    instance._on_error(instance.ws, RuntimeError('nope'))
    assert instance._connected is False

    instance._connected = True
    instance._on_close(instance.ws, 1006, 'abnormal')
    assert instance._connected is False


def test_on_message_ignores_invalid_json(instance):
    instance._on_message(instance.ws, 'not json')

    assert instance.actions == {}


def test_did_receive_global_settings_is_forwarded(instance):
    action = RecordingAction()
    instance.actions['ctx'] = action

    send(instance, event='didReceiveGlobalSettings', payload={'settings': {'a': 1}})

    assert instance.global_settings == {'a': 1}
    assert action.calls == [('on_did_receive_global_settings', ({'a': 1},))]


def test_will_appear_creates_action_and_calls_hook(instance, monkeypatch):
    created = RecordingAction()
    monkeypatch.setattr(
        'streamdock_core.action_factory.ActionFactory.create_action',
        classmethod(lambda cls, action, context, settings, plugin: created),
    )

    send(
        instance,
        event='willAppear',
        context='ctx',
        action='com.qxb.time.time',
        payload={'settings': {'city': '北京'}},
    )

    assert instance.actions == {'ctx': created}
    assert created.calls == [('on_will_appear', ())]


def test_will_appear_does_not_recreate_existing_action(instance, monkeypatch):
    existing = RecordingAction()
    instance.actions['ctx'] = existing
    monkeypatch.setattr(
        'streamdock_core.action_factory.ActionFactory.create_action',
        classmethod(lambda *args, **kwargs: pytest.fail('不应重复创建 Action')),
    )

    send(instance, event='willAppear', context='ctx', action='com.qxb.time.time')

    assert instance.actions['ctx'] is existing


def test_will_appear_without_context_is_ignored(instance, monkeypatch):
    monkeypatch.setattr(
        'streamdock_core.action_factory.ActionFactory.create_action',
        classmethod(lambda *args, **kwargs: pytest.fail('缺少 context 时不应创建 Action')),
    )

    send(instance, event='willAppear', action='com.qxb.time.time')

    assert instance.actions == {}


def test_will_appear_keeps_registry_clean_when_creation_fails(instance, monkeypatch):
    monkeypatch.setattr(
        'streamdock_core.action_factory.ActionFactory.create_action',
        classmethod(lambda *args, **kwargs: None),
    )

    send(instance, event='willAppear', context='ctx', action='com.qxb.time.time')

    assert instance.actions == {}


def test_will_disappear_removes_action_and_calls_hook(instance):
    action = RecordingAction()
    instance.actions['ctx'] = action

    send(instance, event='willDisappear', context='ctx')

    assert instance.actions == {}
    assert action.calls == [('on_will_disappear', ())]


def test_will_disappear_for_unknown_context_is_ignored(instance):
    send(instance, event='willDisappear', context='other')

    assert instance.actions == {}


def test_did_receive_settings_prefers_hook(instance):
    action = RecordingAction()
    instance.actions['ctx'] = action

    send(instance, event='didReceiveSettings', context='ctx', payload={'settings': {'a': 1}})

    assert action.calls == [('on_did_receive_settings', ({'a': 1},))]


def test_did_receive_settings_falls_back_to_attribute(instance):
    action = BareAction()
    instance.actions['ctx'] = action

    send(instance, event='didReceiveSettings', context='ctx', payload={'settings': {'a': 1}})

    assert action.settings == {'a': 1}


def test_title_parameters_did_change_prefers_hook(instance):
    action = RecordingAction()
    instance.actions['ctx'] = action

    send(instance, event='titleParametersDidChange', context='ctx', payload={'title': 'T'})

    assert action.calls == [('on_title_parameters_did_change', ({'title': 'T'},))]


def test_title_parameters_did_change_falls_back_to_attributes(instance):
    action = BareAction()
    instance.actions['ctx'] = action

    send(
        instance,
        event='titleParametersDidChange',
        context='ctx',
        payload={'title': 'T', 'titleParameters': {'fontSize': 12}},
    )

    assert action.title == 'T'
    assert action.title_parameters == {'fontSize': 12}


@pytest.mark.parametrize(
    'event, handler',
    [
        ('keyDown', 'on_key_down'),
        ('keyUp', 'on_key_up'),
        ('dialDown', 'on_dial_down'),
        ('dialUp', 'on_dial_up'),
        ('dialRotate', 'on_dial_rotate'),
    ],
)
def test_context_events_are_dispatched_with_payload(instance, event, handler):
    action = RecordingAction()
    instance.actions['ctx'] = action

    send(instance, event=event, context='ctx', payload={'ticks': 1})

    assert action.calls == [(handler, ({'ticks': 1},))]


def test_context_events_for_unknown_context_are_ignored(instance):
    action = RecordingAction()
    instance.actions['ctx'] = action

    send(instance, event='keyUp', context='missing', payload={})

    assert action.calls == []


@pytest.mark.parametrize(
    'event, handler',
    [
        ('deviceDidConnect', 'on_device_did_connect'),
        ('deviceDidDisconnect', 'on_device_did_disconnect'),
        ('applicationDidLaunch', 'on_application_did_launch'),
        ('applicationDidTerminate', 'on_application_did_terminate'),
        ('systemDidWakeUp', 'on_system_did_wake_up'),
    ],
)
def test_global_events_reach_every_action(instance, event, handler):
    first, second = RecordingAction(context='a'), RecordingAction(context='b')
    instance.actions = {'a': first, 'b': second}

    send(instance, event=event)

    assert [c[0] for c in first.calls] == [handler]
    assert [c[0] for c in second.calls] == [handler]


@pytest.mark.parametrize(
    'event, handler',
    [
        ('propertyInspectorDidAppear', 'on_property_inspector_did_appear'),
        ('propertyInspectorDidDisappear', 'on_property_inspector_did_disappear'),
    ],
)
def test_property_inspector_events_pass_full_message(instance, event, handler):
    action = RecordingAction()
    instance.actions['ctx'] = action

    send(instance, event=event, context='ctx')

    name, args = action.calls[0]
    assert name == handler
    assert args[0]['event'] == event


def test_send_to_plugin_passes_payload(instance):
    action = RecordingAction()
    instance.actions['ctx'] = action

    send(instance, event='sendToPlugin', context='ctx', payload={'action': 'testKey'})

    assert action.calls == [('on_send_to_plugin', ({'action': 'testKey'},))]


def test_unknown_event_is_ignored(instance):
    action = RecordingAction()
    instance.actions['ctx'] = action

    send(instance, event='somethingElse', context='ctx')

    assert action.calls == []
    assert instance.ws.sent == []


def test_set_global_settings_sends_and_stores(instance):
    instance.set_global_settings({'a': 1})

    assert instance.global_settings == {'a': 1}
    assert instance.ws.last_event() == {
        'event': 'setGlobalSettings',
        'context': 'plugin-uuid',
        'payload': {'a': 1},
    }


def test_set_global_settings_survives_send_failure(instance):
    def boom(message):
        raise RuntimeError('socket closed')

    instance.ws.send = boom

    instance.set_global_settings({'a': 1})  # 不应抛出异常

    assert instance.global_settings == {'a': 1}


def test_get_global_settings_requests_settings(instance):
    instance.get_global_settings()

    assert instance.ws.last_event() == {
        'event': 'getGlobalSettings',
        'context': 'plugin-uuid',
    }


def test_send_without_websocket_is_ignored(instance):
    instance.ws = None

    instance.get_global_settings()
    instance.set_global_settings({'a': 1})

    assert instance.global_settings == {'a': 1}


def test_connected_property_reflects_connection_state(instance):
    assert instance.connected is True

    instance._on_close(instance.ws, 1000, 'bye')

    assert instance.connected is False


def test_handler_exception_does_not_propagate(instance):
    class Boom(Action):
        def on_key_up(self, payload):
            raise RuntimeError('boom')

    instance.actions['ctx'] = Boom('com.qxb.time.time', 'ctx', {}, FakePlugin())

    send(instance, event='keyUp', context='ctx', payload={})  # 不应抛出异常


def test_subclass_hook_overrides_are_used(instance):
    class Overriding(Action):
        def __init__(self):
            super().__init__('com.qxb.time.time', 'ctx', {}, FakePlugin())
            self.payloads = []

        def on_key_down(self, payload):
            self.payloads.append(payload)

    action = Overriding()
    instance.actions['ctx'] = action

    send(instance, event='keyDown', context='ctx', payload={'ticks': 2})

    assert action.payloads == [{'ticks': 2}]


def test_get_action_and_get_actions(instance):
    clock = RecordingAction(action='com.qxb.time.time', context='a')
    custom = RecordingAction(action='com.qxb.time.custom', context='b')
    instance.actions = {'a': clock, 'b': custom}

    assert instance.get_action('a') is clock
    assert instance.get_action('missing') is None
    assert instance.get_actions('com.qxb.time.time') == [clock]
    assert instance.get_actions('com.qxb.time.unknown') == []


def test_stop_closes_websocket(instance):
    instance.stop()

    assert instance.ws.closed is True


def test_stop_without_websocket_is_safe(instance):
    instance.ws = None

    instance.stop()


class FakeWebSocketApp:
    """websocket.WebSocketApp 替身，run_forever 时按需模拟连接建立。"""

    connect_on_run = True
    instances = []

    def __init__(self, url, on_open, on_message, on_error, on_close):
        self.url = url
        self.on_open = on_open
        self.on_message = on_message
        self.on_error = on_error
        self.on_close = on_close
        self.sent = []
        self.closed = False
        FakeWebSocketApp.instances.append(self)

    def run_forever(self):
        if FakeWebSocketApp.connect_on_run:
            self.on_open(self)

    def send(self, message):
        self.sent.append(message)

    def close(self):
        self.closed = True


@pytest.fixture
def fake_websocket_app(monkeypatch):
    FakeWebSocketApp.instances = []
    FakeWebSocketApp.connect_on_run = True
    monkeypatch.setattr('streamdock_core.plugin.websocket.WebSocketApp', FakeWebSocketApp)
    monkeypatch.setattr('streamdock_core.plugin.CONNECT_TIMEOUT', 1.0)
    return FakeWebSocketApp


def test_init_connects_and_registers_plugin(fake_websocket_app):
    plugin = Plugin(28196, 'uuid-1', 'registerPlugin', {'application': {}})

    app = fake_websocket_app.instances[0]
    assert app.url == 'ws://127.0.0.1:28196'
    assert plugin.connected is True
    assert json.loads(app.sent[0]) == {'event': 'registerPlugin', 'uuid': 'uuid-1'}
    assert plugin.actions == {}
    assert plugin.info == {'application': {}}
    assert plugin._ws_thread.daemon is True


def test_init_continues_when_connection_times_out(fake_websocket_app, monkeypatch):
    fake_websocket_app.connect_on_run = False
    monkeypatch.setattr('streamdock_core.plugin.CONNECT_TIMEOUT', 0.2)

    plugin = Plugin(28196, 'uuid-1', 'registerPlugin', {})

    assert plugin.connected is False
    assert fake_websocket_app.instances[0].sent == []

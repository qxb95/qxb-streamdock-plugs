import json

import pytest

from src.core.plugin import Plugin

from conftest import FakeTimer, FakeWebSocket


class RecordingAction:
    def __init__(self, action='com.qxb.weather.weather', context='ctx'):
        self.action = action
        self.context = context
        self.settings = {}
        self.title = ''
        self.title_parameters = {}
        self.calls = []

    def __getattr__(self, name):
        if not name.startswith('on_'):
            raise AttributeError(name)

        def handler(*args):
            self.calls.append((name, args))

        return handler


class BareAction:
    def __init__(self, action='com.qxb.weather.weather', context='ctx'):
        self.action = action
        self.context = context
        self.settings = {}
        self.title = ''
        self.title_parameters = {}


@pytest.fixture
def instance():
    """跳过 __init__（会建立真实 WebSocket 连接）构造 Plugin。"""
    plugin = Plugin.__new__(Plugin)
    plugin.actions = {}
    plugin.global_settings = None
    plugin.timer = FakeTimer()
    plugin.plugin_uuid = 'plugin-uuid'
    plugin.http_server = None
    plugin.http_server_thread = None
    plugin.ws = FakeWebSocket()
    return plugin


def send(plugin, **data):
    plugin._on_message(plugin.ws, json.dumps(data))


def test_on_open_registers_plugin(instance):
    instance._on_open(instance.ws, 'registerPlugin', 'uuid-1')

    assert instance.ws.last_event() == {'event': 'registerPlugin', 'uuid': 'uuid-1'}


def test_did_receive_global_settings_is_forwarded(instance):
    action = RecordingAction()
    instance.actions['ctx'] = action

    send(instance, event='didReceiveGlobalSettings', payload={'settings': {'a': 1}})

    assert instance.global_settings == {'a': 1}
    assert action.calls == [('on_did_receive_global_settings', ({'a': 1},))]


def test_will_appear_creates_and_stores_action(instance, monkeypatch):
    created = RecordingAction()
    monkeypatch.setattr(
        'src.core.action_factory.ActionFactory.create_action',
        classmethod(lambda cls, action, context, settings, plugin: created),
    )

    send(
        instance,
        event='willAppear',
        context='ctx',
        action='com.qxb.weather.weather',
        payload={'settings': {'city': '北京'}},
    )

    assert instance.actions == {'ctx': created}


def test_will_appear_passes_settings_to_factory(instance, monkeypatch):
    seen = {}

    def create(cls, action, context, settings, plugin):
        seen.update(action=action, context=context, settings=settings, plugin=plugin)
        return RecordingAction()

    monkeypatch.setattr(
        'src.core.action_factory.ActionFactory.create_action', classmethod(create)
    )

    send(
        instance,
        event='willAppear',
        context='ctx',
        action='com.qxb.weather.weather',
        payload={'settings': {'city': '北京'}},
    )

    assert seen['action'] == 'com.qxb.weather.weather'
    assert seen['context'] == 'ctx'
    assert seen['settings'] == {'city': '北京'}
    assert seen['plugin'] is instance


def test_will_appear_keeps_registry_clean_when_creation_fails(instance, monkeypatch):
    monkeypatch.setattr(
        'src.core.action_factory.ActionFactory.create_action',
        classmethod(lambda *args, **kwargs: None),
    )

    send(instance, event='willAppear', context='ctx', action='com.qxb.weather.weather')

    assert instance.actions == {}


def test_will_disappear_removes_action_and_calls_hook(instance):
    action = RecordingAction()
    instance.actions['ctx'] = action

    send(instance, event='willDisappear', context='ctx')

    assert instance.actions == {}
    assert action.calls == [('on_will_disappear', ())]


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


def test_get_global_settings_requests_settings(instance):
    instance.get_global_settings()

    assert instance.ws.last_event() == {
        'event': 'getGlobalSettings',
        'context': 'plugin-uuid',
    }


def test_get_action_and_get_actions(instance):
    weather = RecordingAction(action='com.qxb.weather.weather', context='a')
    clock = RecordingAction(action='com.qxb.weather.time', context='b')
    instance.actions = {'a': weather, 'b': clock}

    assert instance.get_action('a') is weather
    assert instance.get_action('missing') is None
    assert instance.get_actions('com.qxb.weather.weather') == [weather]
    assert instance.get_actions('com.qxb.weather.unknown') == []


def test_stop_without_http_server_is_safe(instance):
    instance.stop()


def test_stop_shuts_down_http_server(instance):
    class FakeHTTPServer:
        def __init__(self):
            self.shutdown_called = False
            self.closed = False

        def shutdown(self):
            self.shutdown_called = True

        def server_close(self):
            self.closed = True

    instance.http_server = FakeHTTPServer()

    instance.stop()

    assert instance.http_server.shutdown_called is True
    assert instance.http_server.closed is True

import pytest

from src.core.action import Action

from conftest import FakePlugin


@pytest.fixture
def action(plugin):
    return Action('com.qxb.time.time', 'ctx-1', {'city': '北京'}, plugin)


def test_init_stores_arguments(action, plugin):
    assert action.action == 'com.qxb.time.time'
    assert action.context == 'ctx-1'
    assert action.settings == {'city': '北京'}
    assert action.title == ''
    assert action.title_parameters == {}
    assert action.plugin is plugin
    assert action._server is plugin.ws


def test_send_to_property_inspector(action, ws):
    action.send_to_property_inspector({'k': 'v'})

    assert ws.last_event() == {
        'event': 'sendToPropertyInspector',
        'action': 'com.qxb.time.time',
        'context': 'ctx-1',
        'payload': {'k': 'v'},
    }


def test_set_state(action, ws):
    action.set_state(1)

    assert ws.last_event() == {
        'event': 'setState',
        'context': 'ctx-1',
        'payload': {'state': 1},
    }


def test_set_title(action, ws):
    action.set_title('12:00:00')

    assert ws.last_event() == {
        'event': 'setTitle',
        'context': 'ctx-1',
        'payload': {'title': '12:00:00', 'target': 0},
    }


def test_set_settings_updates_local_settings(action, ws):
    action.set_settings({'city': '上海'})

    assert action.settings == {'city': '上海'}
    assert ws.last_event() == {
        'event': 'setSettings',
        'context': 'ctx-1',
        'payload': {'city': '上海'},
    }


def test_open_url(action, ws):
    action.open_url('https://example.com')

    assert ws.last_event() == {
        'event': 'openUrl',
        'payload': {'url': 'https://example.com'},
    }


def test_show_ok_and_show_alert(action, ws):
    action.show_ok()
    action.show_alert()

    assert [e['event'] for e in ws.events] == ['showOk', 'showAlert']
    assert all(e['context'] == 'ctx-1' for e in ws.events)


def test_set_image(action, ws):
    action.set_image('data:image/png;base64,AAA')

    assert ws.last_event() == {
        'event': 'setImage',
        'context': 'ctx-1',
        'payload': {'target': 0, 'image': 'data:image/png;base64,AAA'},
    }


def test_log_message(action, ws):
    action.log_message('hello')

    assert ws.last_event() == {
        'event': 'logMessage',
        'payload': {'message': 'hello'},
    }


def test_no_send_without_server():
    action = Action('a', 'ctx', {}, FakePlugin(ws=None))
    action._server = None

    action.set_title('t')
    action.set_state(0)
    action.set_image('x')
    action.set_settings({'a': 1})
    action.send_to_property_inspector({})
    action.open_url('https://example.com')
    action.show_ok()
    action.show_alert()
    action.log_message('m')

    assert action.settings == {}

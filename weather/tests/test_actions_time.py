import re

import pytest

from src.actions.time import Time


@pytest.fixture
def action(plugin):
    return Time('com.qxb.weather.time', 'ctx-2', {}, plugin)


def test_init_registers_one_second_timer(action, plugin):
    interval = plugin.timer.intervals['time_update_ctx-2']

    assert interval['delay'] == 1000
    assert callable(interval['callback'])


def test_timer_callback_sets_current_time_as_title(action, plugin, ws):
    plugin.timer.intervals['time_update_ctx-2']['callback']()

    title = ws.events_of('setTitle')[-1]['payload']['title']
    assert re.fullmatch(r'\d{2}:\d{2}:\d{2}', title)


def test_on_will_disappear_clears_timer(action, plugin):
    action.on_will_disappear()

    assert plugin.timer.cleared == ['time_update_ctx-2']
    assert plugin.timer.intervals == {}


def test_on_key_up_switches_state(action, ws):
    action.on_key_up({})

    assert ws.events_of('setState')[-1]['payload'] == {'state': 1}


@pytest.mark.parametrize(
    'handler',
    [
        'on_key_down',
        'on_dial_down',
        'on_dial_up',
        'on_dial_rotate',
        'on_device_did_connect',
        'on_device_did_disconnect',
        'on_application_did_launch',
        'on_application_did_terminate',
        'on_system_did_wake_up',
        'on_property_inspector_did_appear',
        'on_property_inspector_did_disappear',
        'on_send_to_plugin',
        'on_did_receive_global_settings',
    ],
)
def test_logging_only_callbacks_send_nothing(action, ws, handler):
    ws.sent.clear()

    getattr(action, handler)({'payload': 'x'})

    assert ws.sent == []

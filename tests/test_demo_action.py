import base64
import io

import pytest
from PIL import Image

from streamdock_core.demo_action import Custom

from tests.fakes import FakePlugin


@pytest.fixture
def custom(plugin):
    return Custom('com.qxb.demo.custom', 'ctx-1', {}, plugin)


def test_init_sends_full_demo_sequence(custom, plugin, ws):
    assert plugin.global_settings_calls == [{'test': 'test'}]
    assert [e['event'] for e in ws.events] == [
        'setImage', 'setSettings', 'logMessage', 'setTitle', 'showAlert',
    ]
    assert custom.settings == {'test': 'test'}


def test_init_image_is_a_valid_png(custom, ws):
    image_url = ws.events_of('setImage')[0]['payload']['image']
    header, encoded = image_url.split(',', 1)

    assert header == 'data:image/png;base64'
    image = Image.open(io.BytesIO(base64.b64decode(encoded)))
    assert image.format == 'PNG'
    assert image.size == (200, 200)


def test_on_will_disappear_clears_timer(custom, plugin):
    custom.on_will_disappear()

    assert plugin.timer.cleared == ['time_update_ctx-1']


def test_on_key_up_sends_all_feedback_events(custom, plugin, ws):
    ws.sent.clear()
    plugin.global_settings_calls.clear()

    custom.on_key_up({'ticks': 1})

    assert plugin.global_settings_calls == [{'test': 'tedasdasdst'}]
    assert [e['event'] for e in ws.events] == [
        'setSettings', 'sendToPropertyInspector', 'openUrl', 'showOk',
    ]
    assert custom.settings == {'test': 'dasdsada'}
    assert ws.events_of('openUrl')[0]['payload']['url'].startswith('https://')


def test_quiet_callbacks_do_not_send_events(custom, ws):
    ws.sent.clear()

    custom.on_key_down({'ticks': 1})
    custom.on_did_receive_global_settings({'a': 1})

    assert ws.sent == []


def test_custom_can_be_created_without_websocket():
    action = Custom('com.qxb.demo.custom', 'ctx', {}, FakePlugin(ws=None))

    assert action.settings == {'test': 'test'}

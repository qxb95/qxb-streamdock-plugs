import base64
import io

import pytest
from PIL import Image

from src.actions.custom import Custom


@pytest.fixture
def action(plugin):
    return Custom('com.qxb.time.custom', 'ctx-9', {}, plugin)


def test_init_pushes_example_image(action, ws):
    image_event = ws.events_of('setImage')[0]
    raw = image_event['payload']['image']

    assert raw.startswith('data:image/png;base64,')
    image = Image.open(io.BytesIO(base64.b64decode(raw.split(',', 1)[1])))
    assert image.size == (200, 200)


def test_init_sends_expected_event_sequence(action, ws):
    assert [e['event'] for e in ws.events] == [
        'setImage',
        'setSettings',
        'logMessage',
        'setTitle',
        'showAlert',
    ]


def test_init_seeds_global_settings(action, plugin):
    assert plugin.global_settings_calls == [{'test': 'test'}]
    assert action.settings == {'test': 'test'}


def test_on_will_disappear_clears_timer(action, plugin):
    action.on_will_disappear()

    assert plugin.timer.cleared == ['time_update_ctx-9']


def test_on_key_up_sends_full_event_sequence(action, ws, plugin):
    ws.sent.clear()

    action.on_key_up({'settings': {}})

    assert [e['event'] for e in ws.events] == [
        'setSettings',
        'sendToPropertyInspector',
        'openUrl',
        'showOk',
    ]
    assert plugin.global_settings_calls[-1] == {'test': 'tedasdasdst'}
    assert action.settings == {'test': 'dasdsada'}


def test_lifecycle_callbacks_do_not_send_events(action, ws):
    ws.sent.clear()

    action.on_key_down({'a': 1})
    action.on_did_receive_global_settings({'b': 2})

    assert ws.sent == []

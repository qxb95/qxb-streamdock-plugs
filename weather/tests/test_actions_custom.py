import base64
import io

import pytest
import requests
from PIL import Image

from src.actions.custom import Custom


@pytest.fixture
def action(plugin):
    return Custom('com.qxb.weather.custom', 'ctx-9', {}, plugin)


class FakeResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload or {}

    def json(self):
        return self._payload


def test_init_pushes_example_image(action, ws):
    raw = ws.events_of('setImage')[0]['payload']['image']

    assert raw.startswith('data:image/png;base64,')
    assert Image.open(io.BytesIO(base64.b64decode(raw.split(',', 1)[1]))).size == (200, 200)


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

    action.on_key_up({})

    assert [e['event'] for e in ws.events] == [
        'setSettings',
        'sendToPropertyInspector',
        'openUrl',
        'showOk',
    ]
    assert plugin.global_settings_calls[-1] == {'test': 'tedasdasdst'}
    assert action.settings == {'test': 'dasdsada'}


def test_on_key_down_queries_both_endpoints(action, monkeypatch):
    urls = []

    def fake_get(url, **kwargs):
        urls.append(url)
        return FakeResponse(payload={'code': '200'})

    monkeypatch.setattr('src.actions.custom.requests.get', fake_get)

    action.on_key_down({})

    assert len(urls) == 2
    assert urls[0] == 'https://localhost:8000/api'
    assert 'geoapi.qweather.com' in urls[1]


def test_on_key_down_logs_non_200_responses(action, monkeypatch):
    monkeypatch.setattr(
        'src.actions.custom.requests.get', lambda url, **kwargs: FakeResponse(status_code=404)
    )

    action.on_key_down({})


def test_on_key_down_propagates_request_errors(action, monkeypatch):
    def boom(url, **kwargs):
        raise requests.ConnectionError('offline')

    monkeypatch.setattr('src.actions.custom.requests.get', boom)

    with pytest.raises(requests.ConnectionError):
        action.on_key_down({})


def test_on_did_receive_global_settings_sends_nothing(action, ws):
    ws.sent.clear()

    action.on_did_receive_global_settings({'a': 1})

    assert ws.sent == []

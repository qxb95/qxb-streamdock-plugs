import base64
import io
import json
import os

import pytest
import requests
from PIL import Image

from src.actions.weather import Weather

RESOURCES = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'resources'
)

LIVE_OK = {
    'status': '1',
    'count': '1',
    'lives': [{'city': '上海市', 'weather': '多云', 'temperature': '21'}],
}


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f'status {self.status_code}')

    def json(self):
        return self._payload


def patch_get(monkeypatch, result):
    """把 requests.get 替换为固定结果，并返回记录到的调用参数。"""
    calls = []

    def fake_get(url, params=None, timeout=None):
        calls.append({'url': url, 'params': params, 'timeout': timeout})
        if isinstance(result, Exception):
            raise result
        return result

    monkeypatch.setattr('src.actions.weather.requests.get', fake_get)
    return calls


@pytest.fixture
def config_path(tmp_path, monkeypatch):
    path = tmp_path / 'config.json'
    monkeypatch.setattr(Weather, '_get_config_path', lambda self: str(path))
    return path


@pytest.fixture
def weather(plugin, config_path):
    """跳过 __init__ 的 Weather 实例，便于单独测试各方法。"""
    action = Weather.__new__(Weather)
    action.action = 'com.qxb.weather.weather'
    action.context = 'ctx-1'
    action.settings = {}
    action.title = ''
    action.title_parameters = {}
    action.plugin = plugin
    action._server = plugin.ws
    action.resources_path = RESOURCES
    action.font_path = os.path.join(RESOURCES, 'iconfont.ttf')
    action._apply_config({})
    return action


def decode_image(data_url):
    assert data_url.startswith('data:image/png;base64,')
    raw = base64.b64decode(data_url.split(',', 1)[1])
    return Image.open(io.BytesIO(raw))


# ---------- 配置 ----------

def test_apply_config_uses_defaults_for_missing_keys(weather):
    weather._apply_config({})

    assert weather.api_key == ''
    assert weather.city == '北京'
    assert (weather.show_city, weather.show_temp, weather.show_desc) == (True, True, True)
    assert weather.font_size == 10
    assert weather.text_color == '#ffffff'
    assert weather.stroke_color == '#000000'
    assert weather.bg_type == 'image'
    assert weather.bg_image == 'bg_default.png'
    assert weather.bg_color == '#2c3e50'


def test_apply_config_reads_every_supported_key(weather):
    weather._apply_config(
        {
            'apiKey': 'k',
            'city': '广州',
            'showCity': False,
            'showTemp': False,
            'showWeatherDesc': False,
            'fontSize': 14,
            'textColor': '#112233',
            'strokeColor': '#445566',
            'bgType': 'color',
            'bgImage': 'bg_dark.png',
            'bgColor': '#000000',
        }
    )

    assert (weather.api_key, weather.city, weather.font_size) == ('k', '广州', 14)
    assert (weather.show_city, weather.show_temp, weather.show_desc) == (False, False, False)
    assert (weather.text_color, weather.stroke_color) == ('#112233', '#445566')
    assert (weather.bg_type, weather.bg_image, weather.bg_color) == ('color', 'bg_dark.png', '#000000')


def test_load_config_prefers_config_file_over_settings(weather, config_path):
    config_path.write_text(json.dumps({'city': '深圳', 'apiKey': 'from-file'}), encoding='utf-8')

    weather._load_and_apply_config({'city': '杭州', 'apiKey': 'from-settings'})

    assert weather.city == '深圳'
    assert weather.api_key == 'from-file'


def test_load_config_uses_settings_when_file_missing(weather):
    weather._load_and_apply_config({'city': '杭州'})

    assert weather.city == '杭州'


def test_load_config_falls_back_to_settings_when_file_is_corrupt(weather, config_path):
    config_path.write_text('{ not json', encoding='utf-8')

    weather._load_and_apply_config({'city': '杭州'})

    assert weather.city == '杭州'


def test_load_config_uses_defaults_without_file_or_settings(weather):
    weather.city = '成都'

    weather._load_and_apply_config(None)

    assert weather.city == '北京'
    assert weather.api_key == ''


def test_save_config_writes_utf8_json(weather, config_path):
    assert weather._save_config({'city': '西安'}) is True

    saved = json.loads(config_path.read_text(encoding='utf-8'))
    assert saved == {'city': '西安'}


def test_save_config_merges_with_existing_file(weather, config_path):
    config_path.write_text(json.dumps({'city': '北京', 'apiKey': 'k'}), encoding='utf-8')

    weather._save_config({'city': '西安'})

    saved = json.loads(config_path.read_text(encoding='utf-8'))
    assert saved == {'city': '西安', 'apiKey': 'k'}


def test_save_config_replaces_corrupt_existing_file(weather, config_path):
    config_path.write_text('broken', encoding='utf-8')

    assert weather._save_config({'city': '西安'}) is True
    assert json.loads(config_path.read_text(encoding='utf-8')) == {'city': '西安'}


def test_save_config_returns_false_when_path_is_not_writable(weather, tmp_path, monkeypatch):
    directory = tmp_path / 'config.json'
    directory.mkdir()
    monkeypatch.setattr(Weather, '_get_config_path', lambda self: str(directory))

    assert weather._save_config({'city': '西安'}) is False


def test_sync_config_pushes_full_settings(weather, ws):
    weather._apply_config({'city': '广州', 'apiKey': 'k', 'fontSize': 12})

    weather._sync_config_to_streamdock()

    payload = ws.events_of('setSettings')[-1]['payload']
    assert payload['city'] == '广州'
    assert payload['apiKey'] == 'k'
    assert payload['fontSize'] == 12
    assert set(payload) == {
        'apiKey',
        'city',
        'showCity',
        'showTemp',
        'showWeatherDesc',
        'fontSize',
        'textColor',
        'strokeColor',
        'bgType',
        'bgImage',
        'bgColor',
    }
    assert weather.settings == payload


# ---------- 高德 API ----------

def test_fetch_weather_returns_normalized_data(weather, monkeypatch):
    weather.api_key = 'secret-key'
    weather.city = '上海'
    calls = patch_get(monkeypatch, FakeResponse(LIVE_OK))

    assert weather.fetch_weather() == {
        'city': '上海市',
        'weather': '多云',
        'temperature': '21',
    }
    assert calls[0]['url'] == 'https://restapi.amap.com/v3/weather/weatherInfo'
    assert calls[0]['params'] == {'city': '上海', 'key': 'secret-key', 'extensions': 'base'}
    assert calls[0]['timeout'] == 5


def test_fetch_weather_skips_request_without_api_key(weather, monkeypatch):
    weather.api_key = ''
    calls = patch_get(monkeypatch, FakeResponse(LIVE_OK))

    assert weather.fetch_weather() is None
    assert calls == []


def test_fetch_weather_masks_short_api_key(weather, monkeypatch):
    weather.api_key = 'ab'
    patch_get(monkeypatch, FakeResponse(LIVE_OK))

    assert weather.fetch_weather() is not None


@pytest.mark.parametrize(
    'payload',
    [
        {'status': '0', 'count': '0', 'info': 'INVALID_USER_KEY'},
        {'status': '1', 'count': '0', 'lives': []},
    ],
)
def test_fetch_weather_returns_none_for_api_errors(weather, monkeypatch, payload):
    weather.api_key = 'k'
    patch_get(monkeypatch, FakeResponse(payload))

    assert weather.fetch_weather() is None


def test_fetch_weather_returns_none_on_request_exception(weather, monkeypatch):
    weather.api_key = 'k'
    patch_get(monkeypatch, requests.ConnectionError('offline'))

    assert weather.fetch_weather() is None


def test_fetch_weather_returns_none_on_http_error(weather, monkeypatch):
    weather.api_key = 'k'
    patch_get(monkeypatch, FakeResponse({}, status_code=500))

    assert weather.fetch_weather() is None


def test_test_api_key_rejects_empty_key(weather):
    assert weather._test_api_key('') == {'success': False, 'error': 'Key 为空'}
    assert weather._test_api_key(None) == {'success': False, 'error': 'Key 为空'}


def test_test_api_key_reports_current_weather(weather, monkeypatch):
    weather.city = '上海'
    calls = patch_get(monkeypatch, FakeResponse(LIVE_OK))

    assert weather._test_api_key('k') == {'success': True, 'weather': '上海市 多云 21°C'}
    assert calls[0]['params']['key'] == 'k'


def test_test_api_key_surfaces_api_error_message(weather, monkeypatch):
    patch_get(monkeypatch, FakeResponse({'status': '0', 'count': '0', 'info': 'INVALID_USER_KEY'}))

    assert weather._test_api_key('k') == {'success': False, 'error': 'INVALID_USER_KEY'}


def test_test_api_key_surfaces_exception_message(weather, monkeypatch):
    patch_get(monkeypatch, requests.Timeout('timed out'))

    result = weather._test_api_key('k')

    assert result['success'] is False
    assert 'timed out' in result['error']


# ---------- 刷新逻辑 ----------

def test_update_weather_pushes_image_and_clears_title(weather, ws, monkeypatch):
    weather.api_key = 'k'
    patch_get(monkeypatch, FakeResponse(LIVE_OK))

    weather.update_weather(force=True)

    assert [e['event'] for e in ws.events] == ['setTitle', 'setImage', 'setTitle']
    assert ws.events_of('setTitle')[0]['payload']['title'] == '加载中...'
    assert ws.events_of('setTitle')[-1]['payload']['title'] == ''
    assert decode_image(ws.events_of('setImage')[0]['payload']['image']).size == (72, 72)


def test_update_weather_shows_error_image_on_failure(weather, ws, monkeypatch):
    weather.api_key = 'k'
    patch_get(monkeypatch, requests.ConnectionError('offline'))

    weather.update_weather(force=True)

    assert ws.events_of('setTitle')[-1]['payload']['title'] == '获取失败'
    assert decode_image(ws.events_of('setImage')[0]['payload']['image']).size == (72, 72)


def test_update_weather_throttles_automatic_refresh(weather, ws, monkeypatch):
    weather.api_key = 'k'
    patch_get(monkeypatch, FakeResponse(LIVE_OK))

    weather.update_weather(force=False)
    events_after_first = len(ws.events)
    weather.update_weather(force=False)

    assert len(ws.events) == events_after_first, '限流窗口内的自动刷新应被跳过'


def test_update_weather_force_ignores_throttle(weather, ws, monkeypatch):
    weather.api_key = 'k'
    patch_get(monkeypatch, FakeResponse(LIVE_OK))
    weather.plugin._last_update_time = 1e12

    weather.update_weather(force=True)

    assert ws.events_of('setImage')


def test_update_weather_refreshes_after_threshold(weather, ws, monkeypatch):
    weather.api_key = 'k'
    patch_get(monkeypatch, FakeResponse(LIVE_OK))

    weather.update_weather(force=False)
    weather.plugin._last_update_time -= weather.REFRESH_THRESHOLD + 1
    ws.sent.clear()
    weather.update_weather(force=False)

    assert ws.events_of('setImage')


def test_update_weather_hot_reloads_config_file(weather, ws, config_path, monkeypatch):
    config_path.write_text(json.dumps({'apiKey': 'k', 'city': '深圳'}), encoding='utf-8')
    calls = patch_get(monkeypatch, FakeResponse(LIVE_OK))

    weather.update_weather(force=True)

    assert weather.city == '深圳'
    assert calls[0]['params']['city'] == '深圳'


def test_update_weather_survives_corrupt_config_file(weather, config_path, monkeypatch):
    config_path.write_text('broken', encoding='utf-8')
    weather.api_key = 'k'
    weather.city = '北京'
    patch_get(monkeypatch, FakeResponse(LIVE_OK))

    weather.update_weather(force=True)

    assert weather.city == '北京'


# ---------- 图片渲染 ----------

def test_get_error_image_returns_72px_png(weather):
    image = decode_image(weather.get_error_image('请检查 Key'))

    assert image.size == (72, 72)
    assert image.format == 'PNG'


def test_generate_button_image_uses_background_image(weather):
    weather._apply_config({'bgType': 'image', 'bgImage': 'bg_dark.png'})

    image = decode_image(weather.generate_button_image(LIVE_OK['lives'][0]))

    assert image.size == (72, 72)
    assert weather.bg_type == 'image'


def test_generate_button_image_falls_back_when_background_missing(weather):
    weather._apply_config({'bgType': 'image', 'bgImage': 'does-not-exist.png'})

    decode_image(weather.generate_button_image(LIVE_OK['lives'][0]))

    assert weather.bg_type == 'color'
    assert weather.bg_color == '#2c3e50'


def test_generate_button_image_uses_solid_color_background(weather):
    weather._apply_config({'bgType': 'color', 'bgColor': '#010203', 'showCity': False,
                           'showTemp': False, 'showWeatherDesc': False})

    image = decode_image(weather.generate_button_image(LIVE_OK['lives'][0]))

    assert (1, 2, 3) in [color for _, color in image.convert('RGB').getcolors(maxcolors=1 << 16)]


def test_generate_button_image_tolerates_invalid_colors(weather):
    weather._apply_config(
        {
            'bgType': 'color',
            'bgColor': 'not-a-color',
            'textColor': 'nope',
            'strokeColor': 'nope-either',
        }
    )

    assert decode_image(weather.generate_button_image(LIVE_OK['lives'][0])).size == (72, 72)


@pytest.mark.parametrize(
    'description',
    ['晴', '雷阵雨伴有冰雹', '小雨转中雨', '外星天气'],
)
def test_generate_button_image_handles_any_weather_description(weather, description):
    data = {'city': '上海市', 'weather': description, 'temperature': '21'}

    assert decode_image(weather.generate_button_image(data)).size == (72, 72)


def test_generate_button_image_without_icon_font(weather, monkeypatch):
    monkeypatch.setattr(weather, 'font_path', '/does/not/exist.ttf')

    assert decode_image(weather.generate_button_image(LIVE_OK['lives'][0])).size == (72, 72)


def test_generate_button_image_renders_selected_lines_only(weather):
    weather._apply_config({'bgType': 'color', 'showCity': True, 'showTemp': False,
                           'showWeatherDesc': False})
    only_city = decode_image(weather.generate_button_image(LIVE_OK['lives'][0])).tobytes()

    weather._apply_config({'bgType': 'color', 'showCity': True, 'showTemp': True,
                           'showWeatherDesc': True})
    everything = decode_image(weather.generate_button_image(LIVE_OK['lives'][0])).tobytes()

    assert only_city != everything


def test_generate_button_image_skips_stroke_when_colors_match(weather):
    weather._apply_config({'bgType': 'color', 'textColor': '#ffffff', 'strokeColor': '#ffffff'})
    plain = decode_image(weather.generate_button_image(LIVE_OK['lives'][0])).tobytes()

    weather._apply_config({'bgType': 'color', 'textColor': '#ffffff', 'strokeColor': '#000000'})
    stroked = decode_image(weather.generate_button_image(LIVE_OK['lives'][0])).tobytes()

    assert plain != stroked


def test_weather_icon_map_has_unknown_fallback():
    assert '未知' in Weather.WEATHER_ICON_MAP
    assert all(len(char) == 1 for char in Weather.WEATHER_ICON_MAP.values())


# ---------- 生命周期 ----------

def test_on_will_disappear_clears_timer(weather, plugin):
    weather.on_will_disappear()

    assert plugin.timer.cleared == ['weather_update_ctx-1']


def test_on_key_down_forces_refresh(weather, monkeypatch):
    forced = []
    monkeypatch.setattr(weather, 'update_weather', lambda force=False: forced.append(force))

    weather.on_key_down({})

    assert forced == [True]


def test_on_did_receive_settings_saves_applies_and_refreshes(weather, config_path, monkeypatch):
    forced = []
    monkeypatch.setattr(weather, 'update_weather', lambda force=False: forced.append(force))

    weather.on_did_receive_settings({'city': '南京', 'apiKey': 'new-key'})

    assert weather.city == '南京'
    assert json.loads(config_path.read_text(encoding='utf-8'))['city'] == '南京'
    assert forced == [True]


def test_on_send_to_plugin_answers_test_key_requests(weather, ws, monkeypatch):
    patch_get(monkeypatch, FakeResponse(LIVE_OK))

    weather.on_send_to_plugin({'action': 'testKey', 'apiKey': 'k'})

    event = ws.events_of('sendToPropertyInspector')[-1]
    assert event['payload'] == {
        'event': 'testKeyResult',
        'payload': {'success': True, 'weather': '上海市 多云 21°C'},
    }


def test_on_send_to_plugin_ignores_unknown_actions(weather, ws):
    weather.on_send_to_plugin({'action': 'somethingElse'})

    assert ws.sent == []


# ---------- 初始化 ----------

def test_init_registers_timer_and_performs_first_refresh(plugin, ws, config_path, monkeypatch):
    config_path.write_text(json.dumps({'apiKey': 'k', 'city': '上海'}), encoding='utf-8')
    patch_get(monkeypatch, FakeResponse(LIVE_OK))

    action = Weather('com.qxb.weather.weather', 'ctx-1', {}, plugin)

    interval = plugin.timer.intervals['weather_update_ctx-1']
    assert interval['delay'] == 1800000
    assert interval['callback'] == action.update_weather
    assert action.city == '上海'
    assert action.resources_path == RESOURCES
    assert action.font_path == os.path.join(RESOURCES, 'iconfont.ttf')
    assert ws.events_of('setImage')


def test_init_without_api_key_shows_error_image(plugin, ws, config_path, monkeypatch):
    calls = patch_get(monkeypatch, FakeResponse(LIVE_OK))

    Weather('com.qxb.weather.weather', 'ctx-1', {}, plugin)

    assert calls == [], '没有 Key 时不应请求高德 API'
    assert ws.events_of('setTitle')[-1]['payload']['title'] == '获取失败'

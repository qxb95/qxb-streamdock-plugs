import base64
import io

import pytest
from PIL import Image

from actions import music as music_module
from actions.music import BUTTON_SIZE, WINDOW_WIDTH, Music


class FakeMusicController:
    def __init__(self):
        self.info = {'title': '', 'artist': '', 'status': 'STOPPED'}
        self.play_pause_calls = 0
        self.closed = False

    def get_media_info(self):
        return self.info

    def play_pause(self):
        self.play_pause_calls += 1
        return True

    def close(self):
        self.closed = True


def decode_image(data_url):
    assert data_url.startswith('data:image/png;base64,')
    raw = base64.b64decode(data_url.split(',', 1)[1])
    return Image.open(io.BytesIO(raw))


@pytest.fixture
def controller(monkeypatch):
    fake = FakeMusicController()
    monkeypatch.setattr(music_module, 'MusicController', lambda: fake)
    return fake


@pytest.fixture
def action(controller, plugin):
    return Music('com.qxb.music.music', 'ctx-1', {}, plugin)


def test_init_registers_fetch_and_scroll_timers(action, plugin):
    intervals = plugin.timer.intervals

    assert intervals['music_fetch_ctx-1']['delay'] == music_module.FETCH_INTERVAL_MS
    assert intervals['music_fetch_ctx-1']['callback'] == action._update_title
    assert intervals['music_scroll_ctx-1']['delay'] == music_module.SCROLL_INTERVAL_MS
    assert intervals['music_scroll_ctx-1']['callback'] == action._apply_scroll


def test_init_renders_placeholder_image(action, ws):
    events = ws.events_of('setImage')

    assert events
    image = decode_image(events[-1]['payload']['image'])
    assert image.size == BUTTON_SIZE
    assert action.full_text == ' 无播放 '
    assert action.is_playing is False


def test_load_background_falls_back_to_solid_colour(monkeypatch, controller, plugin):
    monkeypatch.setattr(Music, '_background_cache', None)
    monkeypatch.setattr(music_module, 'find_resource', lambda *parts: '/missing/icon.png')

    Music('com.qxb.music.music', 'ctx-bg', {}, plugin)

    assert Music._background_cache.size == BUTTON_SIZE
    assert Music._background_cache.getpixel((0, 0)) == music_module.BG_COLOR


def test_load_background_uses_icon_when_available(monkeypatch, tmp_path, controller, plugin):
    icon = tmp_path / 'icon.png'
    Image.new('RGB', (32, 32), color=(10, 20, 30)).save(icon)
    monkeypatch.setattr(Music, '_background_cache', None)
    monkeypatch.setattr(music_module, 'find_resource', lambda *parts: str(icon))

    Music('com.qxb.music.music', 'ctx-icon', {}, plugin)

    assert Music._background_cache.size == BUTTON_SIZE
    assert Music._background_cache.getpixel((0, 0)) == (10, 20, 30)


def test_load_background_falls_back_when_icon_is_invalid(monkeypatch, tmp_path, controller, plugin):
    broken = tmp_path / 'icon.png'
    broken.write_text('not an image')
    monkeypatch.setattr(Music, '_background_cache', None)
    monkeypatch.setattr(music_module, 'find_resource', lambda *parts: str(broken))

    Music('com.qxb.music.music', 'ctx-broken', {}, plugin)

    assert Music._background_cache.getpixel((0, 0)) == music_module.BG_COLOR


def test_load_background_looks_up_icon_via_find_resource(monkeypatch, controller, plugin):
    monkeypatch.setattr(Music, '_background_cache', None)
    requested = []
    monkeypatch.setattr(
        music_module, 'find_resource',
        lambda *parts: requested.append(parts) or '/missing/icon.png',
    )

    Music('com.qxb.music.music', 'ctx-frozen', {}, plugin)

    assert requested == [('icon.png',)]
    assert Music._background_cache.getpixel((0, 0)) == music_module.BG_COLOR


def test_load_background_is_cached(action, controller, plugin):
    cached = Music._background_cache

    Music('com.qxb.music.music', 'ctx-2', {}, plugin)

    assert Music._background_cache is cached


def test_get_font_returns_cached_font_for_default_size(action):
    assert action._get_font(music_module.FONT_SIZE) is Music._font_cache


def test_get_font_falls_back_for_other_sizes(action):
    font = action._get_font(14)

    assert font is not None


def test_text_width_grows_with_text_length(action):
    font = action._get_font(music_module.FONT_SIZE)

    assert music_module.text_width('abcdefghij', font) > music_module.text_width('a', font)


def test_calc_font_size_returns_default_for_short_text(action):
    assert action._calc_font_size('a') == music_module.FONT_SIZE


def test_calc_font_size_shrinks_until_text_fits(action, monkeypatch):
    # 用字号本身当作字体，让文本宽度与字号成正比，便于推算被选中的字号
    monkeypatch.setattr(action, '_get_font', lambda size: size)
    monkeypatch.setattr(music_module, 'text_width', lambda text, font: font * len(text))

    assert action._calc_font_size('xx') == music_module.FONT_SIZE
    assert action._calc_font_size('xxxx') == 22  # 22 * 4 <= WINDOW_WIDTH < 24 * 4


def test_calc_font_size_floor_is_ten(action, monkeypatch):
    monkeypatch.setattr(music_module, 'text_width', lambda text, font: 10_000)

    assert action._calc_font_size('x' * 200) == 10


def test_update_title_uses_media_info(action, controller, ws):
    controller.info = {'title': '青花瓷', 'artist': '周杰伦', 'status': 'PLAYING'}

    action._update_title()

    assert action.full_text == ' 周杰伦 - 青花瓷 '
    assert action.is_playing is True
    assert action.scroll_period == action.full_text_width + 20
    assert action.scroll_pixel_offset in (0, music_module.STEP_PIXELS)


def test_update_title_resets_to_placeholder_when_media_stops(action, controller):
    controller.info = {'title': '青花瓷', 'artist': '周杰伦', 'status': 'PLAYING'}
    action._update_title()

    controller.info = {'title': '', 'artist': '', 'status': 'STOPPED'}
    action._update_title()

    assert action.full_text == ' 无播放 '
    assert action.is_playing is False
    assert action.scroll_period == 0


def test_update_title_handles_missing_media_info(action, controller):
    controller.info = None

    action._update_title()

    assert action.full_text == ' 无播放 '
    assert action.is_playing is False


def test_update_title_keeps_scroll_state_when_text_is_unchanged(action, controller):
    controller.info = {'title': '青花瓷', 'artist': '周杰伦', 'status': 'PLAYING'}
    action._update_title()
    period = action.scroll_period
    offset = action.scroll_pixel_offset

    action._update_title()

    assert action.scroll_period == period
    assert action.scroll_pixel_offset >= offset


def test_apply_scroll_draws_static_image_when_not_playing(action, ws):
    before = len(ws.events_of('setImage'))

    action._apply_scroll()

    assert len(ws.events_of('setImage')) == before + 1
    assert action.scroll_pixel_offset == 0


def test_apply_scroll_advances_offset_for_long_playing_text(action):
    action.is_playing = True
    action.full_text = ' 周杰伦 - 一首很长很长很长很长的歌名 '
    action.full_text_width = WINDOW_WIDTH + 50
    action.scroll_period = action.full_text_width + 20
    action.scroll_pixel_offset = 0

    action._apply_scroll()

    assert action.scroll_pixel_offset == music_module.STEP_PIXELS


def test_scrolling_image_keeps_button_size(action, ws):
    action.is_playing = True
    action.full_text = ' 周杰伦 - 一首很长很长很长很长的歌名 '
    action.full_text_width = WINDOW_WIDTH + 50
    action.scroll_period = action.full_text_width + 20

    action._update_display(30)

    assert decode_image(ws.events_of('setImage')[-1]['payload']['image']).size == BUTTON_SIZE


def test_draw_button_with_offset_falls_back_to_static_without_scroll_period(action):
    action.scroll_period = 0

    assert action._draw_button_with_offset(10) == action._draw_static_button()


def test_scrolling_offsets_produce_different_images(action):
    action.full_text = ' 周杰伦 - 一首很长很长很长很长的歌名 '
    action.full_text_width = WINDOW_WIDTH + 50
    action.scroll_period = action.full_text_width + 20

    assert action._draw_button_with_offset(0) != action._draw_button_with_offset(24)


def test_key_down_toggles_playback_and_refreshes(action, controller, ws):
    controller.info = {'title': '青花瓷', 'artist': '周杰伦', 'status': 'PLAYING'}
    before = len(ws.events_of('setImage'))

    action.on_key_down({})

    assert controller.play_pause_calls == 1
    assert len(ws.events_of('setImage')) > before
    assert action.full_text == ' 周杰伦 - 青花瓷 '


def test_will_disappear_clears_timers_and_closes_controller(action, controller, plugin):
    action.on_will_disappear()

    assert plugin.timer.cleared == ['music_fetch_ctx-1', 'music_scroll_ctx-1']
    assert plugin.timer.intervals == {}
    assert controller.closed is True

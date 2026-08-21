import base64
import io

import pytest
from PIL import Image

from src.actions.time import Time


@pytest.fixture
def small_clock(monkeypatch):
    """避免每次测试渲染 500x500 表盘。"""
    monkeypatch.setattr(
        'src.actions.time.render_clock',
        lambda canvas_size, dial_size: Image.new('RGB', (24, 24), (7, 7, 7)),
    )


def decoded_images(ws):
    images = []
    for event in ws.events_of('setImage'):
        raw = event['payload']['image']
        assert raw.startswith('data:image/png;base64,')
        payload = base64.b64decode(raw.split(',', 1)[1])
        images.append(Image.open(io.BytesIO(payload)))
    return images


def test_init_sends_initial_image_and_registers_timer(plugin, ws, small_clock):
    action = Time('com.qxb.time.time', 'ctx-1', {}, plugin)

    assert action.canvas_size == 500
    assert action.dial_size == 400
    assert action._timer_key == 'time_update_ctx-1'
    assert plugin.timer.intervals['time_update_ctx-1']['delay'] == 1000
    assert plugin.timer.intervals['time_update_ctx-1']['callback'] == action._refresh
    assert len(decoded_images(ws)) == 1


def test_initial_image_is_a_valid_png(plugin, ws, small_clock):
    Time('com.qxb.time.time', 'ctx-1', {}, plugin)

    image = decoded_images(ws)[0]
    assert image.format == 'PNG'
    assert image.size == (24, 24)


def test_timer_tick_pushes_a_new_image(plugin, ws, small_clock):
    action = Time('com.qxb.time.time', 'ctx-1', {}, plugin)

    action._refresh()

    assert len(ws.events_of('setImage')) == 2


def test_render_failure_during_init_does_not_raise(plugin, ws, monkeypatch):
    def boom(canvas_size, dial_size):
        raise RuntimeError('render failed')

    monkeypatch.setattr('src.actions.time.render_clock', boom)

    action = Time('com.qxb.time.time', 'ctx-1', {}, plugin)

    assert ws.events_of('setImage') == []
    assert 'time_update_ctx-1' in plugin.timer.intervals


def test_render_failure_during_tick_does_not_raise(plugin, ws, small_clock, monkeypatch):
    action = Time('com.qxb.time.time', 'ctx-1', {}, plugin)
    monkeypatch.setattr(
        'src.actions.time.render_clock',
        lambda canvas_size, dial_size: (_ for _ in ()).throw(RuntimeError('boom')),
    )

    action._refresh()

    assert len(ws.events_of('setImage')) == 1


def test_on_will_disappear_clears_timer(plugin, small_clock):
    action = Time('com.qxb.time.time', 'ctx-1', {}, plugin)

    action.on_will_disappear()

    assert plugin.timer.cleared == ['time_update_ctx-1']
    assert plugin.timer.intervals == {}


def test_on_key_up_refreshes_image(plugin, ws, small_clock):
    action = Time('com.qxb.time.time', 'ctx-1', {}, plugin)

    action.on_key_up({'settings': {}})

    assert len(ws.events_of('setImage')) == 2


def test_uses_configured_canvas_and_dial_size(plugin, monkeypatch):
    sizes = []

    def record(canvas_size, dial_size):
        sizes.append((canvas_size, dial_size))
        return Image.new('RGB', (8, 8))

    monkeypatch.setattr('src.actions.time.render_clock', record)

    Time('com.qxb.time.time', 'ctx-1', {}, plugin)

    assert sizes == [(500, 400)]

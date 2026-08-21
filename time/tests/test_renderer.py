import datetime

import pytest
from PIL import Image

from src.core import renderer


@pytest.fixture(autouse=True)
def clear_caches():
    renderer._BG_CACHE = None
    renderer._BG_IMAGE = None
    renderer._FONT_CACHE = None
    yield
    renderer._BG_CACHE = None
    renderer._BG_IMAGE = None
    renderer._FONT_CACHE = None


def freeze(monkeypatch, hour, minute, second):
    fixed = datetime.datetime(2024, 1, 2, hour, minute, second)

    class FrozenDateTime(datetime.datetime):
        @classmethod
        def now(cls, tz=None):
            return fixed

    monkeypatch.setattr(renderer.datetime, 'datetime', FrozenDateTime)


def test_render_clock_returns_square_rgb_image():
    img = renderer.render_clock(120, 100)

    assert isinstance(img, Image.Image)
    assert img.size == (120, 120)
    assert img.mode == 'RGB'


def test_render_clock_uses_default_sizes():
    assert renderer.render_clock().size == (500, 500)


def test_render_clock_differs_between_times(monkeypatch):
    freeze(monkeypatch, 3, 0, 0)
    at_three = renderer.render_clock(120, 100).tobytes()
    freeze(monkeypatch, 9, 30, 30)
    at_nine = renderer.render_clock(120, 100).tobytes()

    assert at_three != at_nine, '不同时间应渲染出不同的表盘'


def test_render_clock_is_deterministic_for_same_time(monkeypatch):
    freeze(monkeypatch, 6, 15, 45)

    first = renderer.render_clock(120, 100).tobytes()
    second = renderer.render_clock(120, 100).tobytes()

    assert first == second


def test_background_is_cached_between_renders():
    renderer.render_clock(120, 100)
    cached = renderer._BG_CACHE

    renderer.render_clock(120, 100)

    assert renderer._BG_CACHE is cached
    assert renderer._BG_CACHE._cache_key == (120, 100)


def test_background_cache_is_rebuilt_for_new_size():
    renderer.render_clock(120, 100)
    first = renderer._BG_CACHE

    renderer.render_clock(160, 140)

    assert renderer._BG_CACHE is not first
    assert renderer._BG_CACHE._cache_key == (160, 140)


def test_render_clock_does_not_mutate_cached_background():
    renderer.render_clock(120, 100)
    snapshot = renderer._BG_CACHE.tobytes()

    renderer.render_clock(120, 100)

    assert renderer._BG_CACHE.tobytes() == snapshot


def test_load_background_returns_none_when_no_file(monkeypatch):
    monkeypatch.setattr(renderer.os.path, 'exists', lambda path: False)

    assert renderer._load_background(72) is None


def test_load_background_resizes_local_file(tmp_path, monkeypatch):
    Image.new('RGB', (10, 20), (1, 2, 3)).save(tmp_path / 'background.png')
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        renderer.os.path,
        'exists',
        lambda path: path == 'background.png',
    )

    img = renderer._load_background(72)

    assert img is not None
    assert img.size == (72, 72)
    assert img.mode == 'RGB'


def test_load_background_caches_image_for_same_size(tmp_path, monkeypatch):
    Image.new('RGB', (10, 10), (4, 5, 6)).save(tmp_path / 'background.png')
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        renderer.os.path,
        'exists',
        lambda path: path == 'background.png',
    )

    first = renderer._load_background(72)
    second = renderer._load_background(72)
    resized = renderer._load_background(48)

    assert first is second
    assert resized.size == (48, 48)


def test_load_background_falls_back_when_file_is_not_an_image(tmp_path, monkeypatch):
    (tmp_path / 'background.png').write_text('not an image')
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        renderer.os.path,
        'exists',
        lambda path: path == 'background.png',
    )

    assert renderer._load_background(72) is None


def test_render_clock_falls_back_to_gradient_background(monkeypatch):
    monkeypatch.setattr(renderer, '_load_background', lambda size: None)

    img = renderer.render_clock(120, 100)

    assert img.size == (120, 120)
    assert len(img.getcolors(maxcolors=1 << 16)) > 1, '渐变背景应包含多种颜色'


def test_get_font_is_cached():
    font = renderer._get_font(500)

    assert font is not None
    assert renderer._get_font(200) is font

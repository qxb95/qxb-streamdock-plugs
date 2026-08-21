import base64
import io

from PIL import Image, ImageFont

from streamdock_core import images


def decode(data_url):
    prefix, encoded = data_url.split(',', 1)
    return prefix, base64.b64decode(encoded)


def test_to_data_url_produces_decodable_png():
    image = Image.new('RGB', (12, 8), color=(10, 20, 30))

    prefix, raw = decode(images.to_data_url(image))

    assert prefix == 'data:image/png;base64'
    decoded = Image.open(io.BytesIO(raw))
    assert decoded.format == 'PNG'
    assert decoded.size == (12, 8)
    assert decoded.convert('RGB').getpixel((0, 0)) == (10, 20, 30)


def test_to_data_url_honours_image_format():
    prefix, raw = decode(images.to_data_url(Image.new('RGB', (4, 4)), image_format='JPEG'))

    assert prefix == 'data:image/jpeg;base64'
    assert Image.open(io.BytesIO(raw)).format == 'JPEG'


def test_load_font_uses_first_loadable_candidate(tmp_path, monkeypatch):
    calls = []

    def fake_truetype(path, size):
        calls.append((path, size))
        if path != 'good.ttf':
            raise OSError('missing')
        return 'loaded'

    monkeypatch.setattr(images.ImageFont, 'truetype', fake_truetype)

    assert images.load_font(20, '', 'missing.ttf', 'good.ttf', 'never.ttf') == 'loaded'
    assert calls == [('missing.ttf', 20), ('good.ttf', 20)]


def failing_truetype(tried):
    """让所有字体路径加载失败，但保留 PIL 默认字体（以文件对象加载）可用"""
    real = images.ImageFont.truetype

    def fake_truetype(font=None, size=10, *args, **kwargs):
        if not isinstance(font, str):
            return real(font, size, *args, **kwargs)
        tried.append(font)
        raise OSError('missing')

    return fake_truetype


def test_load_font_falls_back_to_default(monkeypatch):
    monkeypatch.setattr(images.ImageFont, 'truetype', failing_truetype([]))

    font = images.load_font(14, 'nope.ttf')

    assert isinstance(font, (ImageFont.ImageFont, ImageFont.FreeTypeFont))


def test_load_font_without_candidates_tries_defaults(monkeypatch):
    tried = []
    monkeypatch.setattr(images.ImageFont, 'truetype', failing_truetype(tried))

    images.load_font(10)

    assert tried == list(images.DEFAULT_FONT_CANDIDATES)


def test_text_width_grows_with_more_characters():
    assert images.text_width('mmmm') > images.text_width('m') > 0


def test_text_width_of_empty_text_is_zero():
    assert images.text_width('') == 0


def test_text_width_accepts_explicit_font():
    font = images.load_font(24)

    assert images.text_width('12:00', font) > images.text_width('1', font) > 0

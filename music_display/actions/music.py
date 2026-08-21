import os
from PIL import Image, ImageDraw

from streamdock_core import Action, Logger
from streamdock_core.images import load_font, text_width, to_data_url
from streamdock_core.paths import find_resource

from core.music_controller import MusicController

SCROLL_INTERVAL_MS = 120
STEP_PIXELS = 2
FETCH_INTERVAL_MS = 500          # 缩短至 0.5 秒，更快响应
BUTTON_SIZE = (100, 100)
FONT_SIZE = 28
FONT_PATH = 'C:/Windows/Fonts/msyh.ttc'
TEXT_COLOR = (255, 255, 255)
BG_COLOR = (30, 30, 50)
PADDING = 6
WINDOW_WIDTH = BUTTON_SIZE[0] - 2 * PADDING

class Music(Action):
    _background_cache = None
    _font_cache = None

    def __init__(self, action: str, context: str, settings: dict, plugin):
        super().__init__(action, context, settings, plugin)
        self.music = MusicController()
        self.full_text = " 无播放 "
        self.scroll_pixel_offset = 0
        self._cached_font_size = FONT_SIZE
        self.full_text_width = 0
        self.scroll_period = 0
        self.is_playing = False

        self._load_background()
        self._init_font()

        self.plugin.timer.set_interval(
            f'music_fetch_{context}',
            FETCH_INTERVAL_MS,
            self._update_title
        )
        self.plugin.timer.set_interval(
            f'music_scroll_{context}',
            SCROLL_INTERVAL_MS,
            self._apply_scroll
        )
        self._update_title()
        Logger.info("[Music] 初始化完成")

    def _load_background(self):
        if Music._background_cache is not None:
            return
        icon_path = find_resource('icon.png')
        if os.path.exists(icon_path):
            try:
                img = Image.open(icon_path).convert('RGB').resize(BUTTON_SIZE)
                Music._background_cache = img
                Logger.info("[Music] 已加载背景图片")
            except Exception as e:
                Logger.error(f"[Music] 背景加载失败: {e}")
        if Music._background_cache is None:
            Music._background_cache = Image.new('RGB', BUTTON_SIZE, color=BG_COLOR)

    def _init_font(self):
        if Music._font_cache is None:
            Music._font_cache = load_font(FONT_SIZE, FONT_PATH)

    def _get_font(self, size):
        if size == FONT_SIZE and Music._font_cache is not None:
            return Music._font_cache
        return load_font(size, FONT_PATH)

    def _calc_font_size(self, text):
        for size in range(FONT_SIZE, 10, -2):
            if text_width(text, self._get_font(size)) <= WINDOW_WIDTH:
                return size
        return 10

    def _draw_static_button(self):
        img = Music._background_cache.copy()
        draw = ImageDraw.Draw(img)
        font = self._get_font(self._cached_font_size)
        text = self.full_text
        tw = text_width(text, font)
        th = font.getmetrics()[1]
        x = (BUTTON_SIZE[0] - tw) // 2
        y = (BUTTON_SIZE[1] - th) // 2
        draw.text((x, y), text, fill=TEXT_COLOR, font=font)
        return to_data_url(img)

    def _draw_button_with_offset(self, offset_px):
        if self.scroll_period == 0:
            return self._draw_static_button()
        offset = offset_px % self.scroll_period
        img = Music._background_cache.copy()
        draw = ImageDraw.Draw(img)
        font = self._get_font(self._cached_font_size)
        text = self.full_text
        tw = text_width(text, font)
        th = font.getmetrics()[1]
        base_x = (BUTTON_SIZE[0] - tw) // 2
        draw_y = (BUTTON_SIZE[1] - th) // 2
        draw_x1 = base_x - offset
        draw.text((draw_x1, draw_y), text, fill=TEXT_COLOR, font=font)
        draw_x2 = draw_x1 + self.scroll_period
        draw.text((draw_x2, draw_y), text, fill=TEXT_COLOR, font=font)
        crop_box = (PADDING, 0, PADDING + WINDOW_WIDTH, BUTTON_SIZE[1])
        cropped = img.crop(crop_box)
        final_img = Music._background_cache.copy()
        final_img.paste(cropped, (PADDING, 0))
        return to_data_url(final_img)

    def _update_display(self, offset_px=None):
        if offset_px is None:
            img_base64 = self._draw_static_button()
        else:
            img_base64 = self._draw_button_with_offset(offset_px)
        self.set_image(img_base64)

    def on_will_disappear(self):
        self.plugin.timer.clear_interval(f'music_fetch_{self.context}')
        self.plugin.timer.clear_interval(f'music_scroll_{self.context}')
        self.music.close()

    def on_key_down(self, payload: dict):
        # 发送多媒体键（自动双向切换）
        if not self.music.play_pause():
            self.show_alert()
        # 立即刷新状态（不再等待定时器）
        self._update_title()

    def _update_title(self):
        info = self.music.get_media_info()
        if info and info['title']:
            new_text = f" {info['artist']} - {info['title']} "
            self.is_playing = (info['status'] == 'PLAYING')
        else:
            new_text = " 无播放 "
            self.is_playing = False

        if new_text != self.full_text:
            self.full_text = new_text
            if new_text != " 无播放 ":
                self._cached_font_size = self._calc_font_size(new_text)
                font = self._get_font(self._cached_font_size)
                self.full_text_width = text_width(new_text, font)
                self.scroll_period = self.full_text_width + 20
                self.scroll_pixel_offset = 0
            else:
                self.scroll_period = 0

        self._apply_scroll()

    def _apply_scroll(self):
        if not self.is_playing or self.scroll_period == 0 or self.full_text_width <= WINDOW_WIDTH:
            self._update_display()
            return
        self.scroll_pixel_offset += STEP_PIXELS
        self._update_display(self.scroll_pixel_offset)
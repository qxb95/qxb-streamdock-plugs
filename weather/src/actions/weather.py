import sys
import os
import json
import base64
import io
import time
import requests
from PIL import Image, ImageDraw, ImageFont
from src.core.action import Action
from src.core.logger import Logger

class Weather(Action):
    WEATHER_ICON_MAP = {
        "晴": "\ue602",
        "多云": "\ue614",
        "阴": "\ue601",
        "小雨": "\ue606",
        "中雨": "\ue607",
        "大雨": "\ue60a",
        "雷阵雨": "\ue608",
        "雷阵雨伴有冰雹": "\ue60b",
        "小雪": "\ue605",
        "中雪": "\ue60f",
        "大雪": "\ue609",
        "雨夹雪": "\ue611",
        "冻雨": "\ue612",
        "雾": "\ue603",
        "沙尘": "\ue60d",
        "风": "\ue613",
        "冰雹": "\ue610",
        "雷电": "\ue604",
        "未知": "\ue60c",
    }

    # 限流时间阈值（秒），在此时间内重复的自动刷新将被跳过
    REFRESH_THRESHOLD = 30   # 可调整为 120、300 等

    def __init__(self, action, context, settings, plugin):
        super().__init__(action, context, settings, plugin)

        # 加载配置（优先 config.json）
        self._load_and_apply_config(settings)
        # 同步到 StreamDock 存储（供前端读取）
        self._sync_config_to_streamdock()

        # 资源路径
        if getattr(sys, 'frozen', False):
            exe_dir = os.path.dirname(sys.executable)
            external_res = os.path.join(exe_dir, 'resources')
            if os.path.exists(external_res):
                self.resources_path = external_res
                Logger.info(f"[Weather] 使用外部资源: {self.resources_path}")
            else:
                self.resources_path = os.path.join(sys._MEIPASS, 'resources')
                Logger.info(f"[Weather] 使用内置资源: {self.resources_path}")
        else:
            base_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            self.resources_path = os.path.join(base_path, 'resources')
            Logger.info(f"[Weather] 开发环境资源: {self.resources_path}")

        self.font_path = os.path.join(self.resources_path, 'iconfont.ttf')
        Logger.info(f"[Weather] 字体路径: {self.font_path}")

        # 定时更新（30分钟）
        self.plugin.timer.set_interval(
            f'weather_update_{context}',
            1800000,
            self.update_weather   # 定时器触发为非强制刷新
        )

        # 首次加载时立即刷新（不受限流影响，因为 last_update 为 0）
        self.update_weather(force=False)
        Logger.info(f"[Weather] 初始化完成，城市: {self.city}")

    # ---------- 配置相关 ----------
    def _get_config_path(self):
        if getattr(sys, 'frozen', False):
            return os.path.join(os.path.dirname(sys.executable), 'config.json')
        else:
            return os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'config.json')

    def _load_and_apply_config(self, settings=None):
        config_path = self._get_config_path()
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                Logger.info(f"[Weather] 从 {config_path} 加载配置")
                self._apply_config(config)
                return
            except Exception as e:
                Logger.error(f"[Weather] 读取 {config_path} 失败: {e}")

        if settings:
            Logger.info("[Weather] 使用属性检查器设置")
            self._apply_config(settings)
        else:
            Logger.warning("[Weather] 未找到任何配置，使用默认值")
            self.api_key = ""
            self.city = "北京"
            self.show_city = True
            self.show_temp = True
            self.show_desc = True
            self.font_size = 10
            self.text_color = "#ffffff"
            self.stroke_color = "#000000"
            self.bg_type = 'image'
            self.bg_image = 'bg_default.png'
            self.bg_color = '#2c3e50'

    def _apply_config(self, config):
        self.api_key = config.get('apiKey', "")
        self.city = config.get('city', "北京")
        self.show_city = config.get('showCity', True)
        self.show_temp = config.get('showTemp', True)
        self.show_desc = config.get('showWeatherDesc', True)
        self.font_size = config.get('fontSize', 10)
        self.text_color = config.get('textColor', "#ffffff")
        self.stroke_color = config.get('strokeColor', "#000000")
        self.bg_type = config.get('bgType', 'image')
        self.bg_image = config.get('bgImage', 'bg_default.png')
        self.bg_color = config.get('bgColor', '#2c3e50')

    def _save_config(self, config):
        config_path = self._get_config_path()
        existing = {}
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    existing = json.load(f)
            except Exception as e:
                Logger.warning(f"[Weather] 读取现有 config.json 失败: {e}，将创建新文件")
        existing.update(config)
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(existing, f, ensure_ascii=False, indent=4)
            Logger.info(f"[Weather] 配置已保存到 {config_path}")
            return True
        except Exception as e:
            Logger.error(f"[Weather] 保存 config.json 失败: {e}")
            return False

    def _sync_config_to_streamdock(self):
        config = {
            "apiKey": self.api_key,
            "city": self.city,
            "showCity": self.show_city,
            "showTemp": self.show_temp,
            "showWeatherDesc": self.show_desc,
            "fontSize": self.font_size,
            "textColor": self.text_color,
            "strokeColor": self.stroke_color,
            "bgType": self.bg_type,
            "bgImage": self.bg_image,
            "bgColor": self.bg_color
        }
        self.set_settings(config)
        Logger.info("[Weather] 已同步配置到 StreamDock 存储")

    # ---------- 生命周期回调 ----------
    def on_will_disappear(self):
        self.plugin.timer.clear_interval(f'weather_update_{self.context}')
        Logger.info("[Weather] 按钮消失")

    def on_key_down(self, payload: dict):
        Logger.info("[Weather] 手动刷新（按键触发）")
        self.update_weather(force=True)   # 强制刷新，忽略限流

    def on_did_receive_settings(self, settings: dict):
        Logger.info(f"[Weather] 收到新设置: {settings}")
        self._save_config(settings)
        self._apply_config(settings)
        self._sync_config_to_streamdock()
        self.update_weather(force=True)   # 用户主动保存，强制刷新

    def on_send_to_plugin(self, payload: dict):
        action = payload.get('action')
        if action == 'testKey':
            api_key = payload.get('apiKey')
            Logger.info(f"[Weather] 收到测试 Key 请求")
            result = self._test_api_key(api_key)
            self.send_to_property_inspector({"event": "testKeyResult", "payload": result})

    def _test_api_key(self, api_key):
        if not api_key or api_key == "":
            return {"success": False, "error": "Key 为空"}
        url = "https://restapi.amap.com/v3/weather/weatherInfo"
        params = {
            "city": self.city,
            "key": api_key,
            "extensions": "base"
        }
        try:
            resp = requests.get(url, params=params, timeout=5)
            resp.raise_for_status()
            result = resp.json()
            if result["status"] == "1" and int(result["count"]) > 0:
                live = result["lives"][0]
                return {
                    "success": True,
                    "weather": f"{live['city']} {live['weather']} {live['temperature']}°C"
                }
            else:
                return {"success": False, "error": result.get('info', '未知错误')}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ---------- 核心业务 ----------
    def update_weather(self, force=False):
        """
        刷新天气数据并更新按键显示。
        :param force: 是否强制刷新（忽略限流检查），True 时必定刷新
        """
        # ---- 限流检查（仅在非强制时生效） ----
        if not force:
            now = time.time()
            if not hasattr(self.plugin, '_last_update_time'):
                self.plugin._last_update_time = 0
            if now - self.plugin._last_update_time < self.REFRESH_THRESHOLD:
                Logger.info(f"[Weather] 距上次自动刷新不足 {self.REFRESH_THRESHOLD} 秒，跳过本次刷新")
                return
            self.plugin._last_update_time = now
        else:
            Logger.info("[Weather] 强制刷新模式")

        # ---- 热加载配置 ----
        config_path = self._get_config_path()
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                self._apply_config(config)
                self._sync_config_to_streamdock()
            except Exception as e:
                Logger.error(f"[Weather] 热加载配置失败: {e}")

        Logger.info(f"[Weather] 开始获取天气，城市: {self.city}")
        self.set_title("加载中...")
        data = self.fetch_weather()
        if data is None:
            self.set_title("获取失败")
            self.set_image(self.get_error_image("请检查 Key"))
            return
        img_base64 = self.generate_button_image(data)
        self.set_image(img_base64)
        self.set_title("")
        Logger.info(f"[Weather] 更新成功: {data['city']} {data['weather']} {data['temperature']}°C")

    def fetch_weather(self):
        if not self.api_key:
            Logger.warning("[Weather] API Key 为空，跳过天气获取")
            return None
        url = "https://restapi.amap.com/v3/weather/weatherInfo"
        params = {
            "city": self.city,
            "key": self.api_key,
            "extensions": "base"
        }
        Logger.info(f"[Weather] 请求参数: city={self.city}, key={self.api_key[:4] if len(self.api_key) > 4 else ''}****{self.api_key[-4:] if len(self.api_key) > 4 else ''}")
        try:
            resp = requests.get(url, params=params, timeout=5)
            resp.raise_for_status()
            result = resp.json()
            if result["status"] == "1" and int(result["count"]) > 0:
                live = result["lives"][0]
                return {
                    "city": live["city"],
                    "weather": live["weather"],
                    "temperature": live["temperature"]
                }
            else:
                Logger.error(f"高德 API 返回错误: {result.get('info', '未知错误')}")
                return None
        except Exception as e:
            Logger.error(f"请求天气 API 异常: {e}")
            return None

    def get_error_image(self, msg="错误"):
        img = Image.new("RGB", (72, 72), (44, 62, 80))
        draw = ImageDraw.Draw(img)
        try:
            if os.name == 'nt':
                font_path = "C:/Windows/Fonts/msyh.ttc"
            else:
                font_path = "/System/Library/Fonts/PingFang.ttc"
            font = ImageFont.truetype(font_path, 10)
        except:
            font = ImageFont.load_default()
        try:
            bbox = draw.textbbox((0, 0), msg, font=font)
            w = bbox[2] - bbox[0]
            h = bbox[3] - bbox[1]
        except AttributeError:
            w, h = draw.textsize(msg, font=font)
        x = (72 - w) // 2
        y = (72 - h) // 2
        draw.text((x, y), msg, font=font, fill=(255, 200, 200))
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        return f"data:image/png;base64,{base64.b64encode(buffered.getvalue()).decode()}"

    def generate_button_image(self, data):
        output_size = (72, 72)

        bg = None
        if self.bg_type == 'image':
            bg_path = os.path.join(self.resources_path, self.bg_image)
            try:
                bg_img = Image.open(bg_path).convert("RGBA")
                bg_img = bg_img.resize(output_size, Image.Resampling.LANCZOS)
                if bg_img.mode == 'RGBA':
                    bg = Image.new("RGB", output_size, (255, 255, 255))
                    bg.paste(bg_img, (0, 0), bg_img)
                else:
                    bg = bg_img.convert("RGB")
                Logger.info(f"[Weather] 加载背景图片: {bg_path}")
            except Exception as e:
                Logger.error(f"[Weather] 加载背景图片失败: {e}，使用纯色回退")
                self.bg_type = 'color'
                self.bg_color = "#2c3e50"
        if bg is None:
            try:
                color = self.bg_color.lstrip('#')
                r, g, b = tuple(int(color[i:i+2], 16) for i in (0, 2, 4))
                bg = Image.new("RGB", output_size, (r, g, b))
            except:
                bg = Image.new("RGB", output_size, (44, 62, 80))

        draw = ImageDraw.Draw(bg)

        icon_font = None
        try:
            icon_font = ImageFont.truetype(self.font_path, 32)
        except Exception as e:
            Logger.error(f"[Weather] 加载 iconfont 失败: {e}")

        weather_desc = data['weather']
        icon_char = self.WEATHER_ICON_MAP.get(weather_desc)
        if not icon_char:
            for key, char in self.WEATHER_ICON_MAP.items():
                if key in weather_desc:
                    icon_char = char
                    break
            if not icon_char:
                icon_char = self.WEATHER_ICON_MAP.get("未知", "\ue60c")

        if icon_font:
            try:
                bbox = draw.textbbox((0, 0), icon_char, font=icon_font)
                icon_width = bbox[2] - bbox[0]
            except AttributeError:
                icon_width, _ = draw.textsize(icon_char, font=icon_font)
            icon_x = (output_size[0] - icon_width) // 2
            icon_y = 2
            draw.text((icon_x, icon_y), icon_char, font=icon_font, fill=(255, 255, 255))
        else:
            draw.text((30, 2), "?", font=ImageFont.load_default(), fill=(255, 255, 255))

        # 解析字体颜色
        try:
            hex_color = self.text_color.lstrip('#')
            text_rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        except:
            text_rgb = (255, 255, 255)

        # 解析描边颜色
        try:
            hex_stroke = self.stroke_color.lstrip('#')
            stroke_rgb = tuple(int(hex_stroke[i:i+2], 16) for i in (0, 2, 4))
        except:
            stroke_rgb = (0, 0, 0)

        try:
            if os.name == 'nt':
                text_font_path = "C:/Windows/Fonts/msyh.ttc"
            else:
                text_font_path = "/System/Library/Fonts/PingFang.ttc"
            text_font = ImageFont.truetype(text_font_path, self.font_size)
        except:
            text_font = ImageFont.load_default()

        lines = []
        if self.show_city:
            lines.append(data['city'])
        if self.show_temp:
            lines.append(f"{data['temperature']}°C")
        if self.show_desc:
            lines.append(data['weather'])

        if lines:
            total_height = 0
            line_heights = []
            for line in lines:
                try:
                    bbox = draw.textbbox((0, 0), line, font=text_font)
                    h = bbox[3] - bbox[1]
                except AttributeError:
                    _, h = draw.textsize(line, font=text_font)
                line_heights.append(h)
                total_height += h
            spacing = 2
            total_height += spacing * (len(lines) - 1)

            icon_bottom = icon_y + 30
            available_y = output_size[1] - icon_bottom - 4
            start_y = icon_bottom + (available_y - total_height) // 2
            if start_y < icon_bottom + 2:
                start_y = icon_bottom + 2

            y = start_y
            for idx, line in enumerate(lines):
                try:
                    bbox = draw.textbbox((0, 0), line, font=text_font)
                    w = bbox[2] - bbox[0]
                except AttributeError:
                    w, _ = draw.textsize(line, font=text_font)
                x = (output_size[0] - w) // 2

                # 如果字体颜色与描边相同，直接绘制纯色文字
                if text_rgb == stroke_rgb:
                    draw.text((x, y), line, font=text_font, fill=text_rgb)
                else:
                    # 否则带描边
                    for dx in (-1, 0, 1):
                        for dy in (-1, 0, 1):
                            if dx != 0 or dy != 0:
                                draw.text((x+dx, y+dy), line, font=text_font, fill=stroke_rgb)
                    draw.text((x, y), line, font=text_font, fill=text_rgb)

                y += line_heights[idx] + spacing

        buffered = io.BytesIO()
        bg.save(buffered, format="PNG")
        img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
        return f"data:image/png;base64,{img_base64}"
# -*- coding: utf-8 -*-
"""
NAS 监控 Action - 修复标题覆盖问题
"""
import os
import sys
import base64
import requests
from io import BytesIO
from typing import Dict, Any, Optional, List
from PIL import Image, ImageDraw, ImageFont, ImageFilter

from src.core.action import Action
from src.core.logger import Logger

# ==================== 颜色工具 ====================
def hsv_to_rgb(h, s, v):
    if s == 0:
        return (int(v*255), int(v*255), int(v*255))
    h = h / 60
    i = int(h)
    f = h - i
    p = v * (1 - s)
    q = v * (1 - s * f)
    t = v * (1 - s * (1 - f))
    if i == 0:
        r, g, b = v, t, p
    elif i == 1:
        r, g, b = q, v, p
    elif i == 2:
        r, g, b = p, v, t
    elif i == 3:
        r, g, b = p, q, v
    elif i == 4:
        r, g, b = t, p, v
    else:
        r, g, b = v, p, q
    return (int(r*255), int(g*255), int(b*255))

def get_color_by_percent(percent):
    hue = 120 - (percent / 100) * 120
    main_rgb = hsv_to_rgb(hue, 0.9, 0.7)
    glow_rgb = hsv_to_rgb(hue, 0.8, 0.5)
    return main_rgb, glow_rgb

def get_font(size):
    font_paths = [
        os.path.join(os.path.dirname(__file__), "..", "..", "fonts", "NotoSansSC-Regular.otf"),
        os.path.join(os.path.dirname(__file__), "..", "..", "fonts", "simhei.ttf"),
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/simsun.ttc",
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/STHeiti Light.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
    ]
    for path in font_paths:
        try:
            return ImageFont.truetype(path, size)
        except:
            continue
    return ImageFont.load_default()

def generate_float_ball(stats: Dict, size=(100, 100), metric='cpu',
                        background=None, ball_scale=0.9):
    percent_fields = ['cpu', 'Cpu', 'mp', 's', 'dp', 'gpu_pct']
    if metric not in percent_fields:
        Logger.warning(f"指标 '{metric}' 不是百分比，使用 'cpu'")
        metric = 'cpu'

    value = stats.get(metric, 0)
    if not isinstance(value, (int, float)):
        value = 0
    percent = max(0, min(100, value))

    main_color, glow_color = get_color_by_percent(percent)

    if background is not None:
        bg = background.resize(size, Image.Resampling.LANCZOS)
        if bg.mode in ('RGBA', 'LA'):
            bg = bg.convert('RGB')
        img = bg.convert('RGBA')
    else:
        img = Image.new('RGBA', size, (0, 0, 0, 0))

    w, h = size
    cx, cy = w // 2, h // 2
    base_radius = min(w, h) // 2 - 6
    r = int(base_radius * ball_scale)
    if r < 10:
        r = 10

    ball_layer = Image.new('RGBA', size, (0, 0, 0, 0))

    glow_img = Image.new('RGBA', size, (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow_img)
    glow_radius = r + 6
    glow_draw.ellipse([cx - glow_radius, cy - glow_radius, cx + glow_radius, cy + glow_radius],
                      fill=(glow_color[0], glow_color[1], glow_color[2], 60))
    glow_img = glow_img.filter(ImageFilter.GaussianBlur(radius=4))
    ball_layer = Image.alpha_composite(ball_layer, glow_img)

    ball_body = Image.new('RGBA', size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(ball_body)
    steps = 20
    for i in range(steps, 0, -1):
        ratio = i / steps
        radius = r * ratio
        edge_color = (int(main_color[0] * 0.3),
                      int(main_color[1] * 0.3),
                      int(main_color[2] * 0.3))
        center_color = (min(255, int(main_color[0] * 1.3)),
                        min(255, int(main_color[1] * 1.3)),
                        min(255, int(main_color[2] * 1.3)))
        r_col = int(edge_color[0] + (center_color[0] - edge_color[0]) * (1 - ratio))
        g_col = int(edge_color[1] + (center_color[1] - edge_color[1]) * (1 - ratio))
        b_col = int(edge_color[2] + (center_color[2] - edge_color[2]) * (1 - ratio))
        draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius],
                     fill=(r_col, g_col, b_col, 255))
    ball_layer = Image.alpha_composite(ball_layer, ball_body)

    highlight_img = Image.new('RGBA', size, (0, 0, 0, 0))
    h_draw = ImageDraw.Draw(highlight_img)
    h_x1 = cx - r * 0.6
    h_y1 = cy - r * 0.7
    h_x2 = cx + r * 0.2
    h_y2 = cy - r * 0.2
    h_draw.ellipse([h_x1, h_y1, h_x2, h_y2],
                   fill=(255, 255, 255, 180))
    h2_x1 = cx - r * 0.3
    h2_y1 = cy - r * 0.9
    h2_x2 = cx + r * 0.1
    h2_y2 = cy - r * 0.5
    h_draw.ellipse([h2_x1, h2_y1, h2_x2, h2_y2],
                   fill=(255, 255, 255, 100))
    highlight_img = highlight_img.filter(ImageFilter.GaussianBlur(radius=2))
    ball_layer = Image.alpha_composite(ball_layer, highlight_img)

    reflection_img = Image.new('RGBA', size, (0, 0, 0, 0))
    r_draw = ImageDraw.Draw(reflection_img)
    r_draw.ellipse([cx - r * 0.8, cy + r * 0.3, cx + r * 0.8, cy + r * 0.9],
                   fill=(255, 255, 255, 30))
    reflection_img = reflection_img.filter(ImageFilter.GaussianBlur(radius=3))
    ball_layer = Image.alpha_composite(ball_layer, reflection_img)

    img = Image.alpha_composite(img, ball_layer)

    draw = ImageDraw.Draw(img)
    try:
        num_font = ImageFont.truetype("arialbd.ttf", int(r * 0.6))
    except:
        num_font = get_font(int(r * 0.6))
    label_font = get_font(int(r * 0.2))

    cn_map = {'cpu': 'CPU', 'Cpu': 'CPU', 'mp': '内存', 's': 'Swap', 'dp': '磁盘', 'gpu_pct': 'GPU'}
    label = cn_map.get(metric, metric.upper())

    text = f"{percent:.1f}%"
    text_bbox = draw.textbbox((0, 0), text, font=num_font)
    text_w = text_bbox[2] - text_bbox[0]
    text_h = text_bbox[3] - text_bbox[1]
    x_text = cx - text_w // 2
    y_text = cy - text_h // 2 - 2
    outline_color = (0, 0, 0, 200)
    for dx, dy in [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]:
        draw.text((x_text + dx, y_text + dy), text, font=num_font, fill=outline_color)
    draw.text((x_text, y_text), text, font=num_font, fill=(255, 255, 255, 255))

    label_bbox = draw.textbbox((0, 0), label, font=label_font)
    label_w = label_bbox[2] - label_bbox[0]
    x_label = cx - label_w // 2
    y_label = cy + int(r * 0.4)
    draw.text((x_label, y_label), label, font=label_font, fill=(200, 200, 200, 255))

    return img


# ==================== Beszel 客户端 ====================
class BeszelClient:
    def __init__(self, base_url: str, email: str, password: str):
        self.base_url = base_url.rstrip('/')
        self.email = email
        self.password = password
        self.token = None
        self._authenticate()

    def _authenticate(self):
        auth_url = f"{self.base_url}/api/collections/users/auth-with-password"
        try:
            resp = requests.post(auth_url, json={"identity": self.email, "password": self.password}, timeout=10)
            resp.raise_for_status()
            self.token = resp.json()['token']
            Logger.info("Beszel 认证成功")
        except Exception as e:
            Logger.error(f"Beszel 认证失败: {e}")
            raise

    def _request(self, method, path, params=None, data=None):
        headers = {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}
        resp = requests.request(method, f"{self.base_url}{path}", headers=headers,
                                params=params, json=data, timeout=10)
        resp.raise_for_status()
        return resp.json()

    def list_systems(self) -> List[Dict]:
        return self._request('GET', '/api/collections/systems/records').get('items', [])

    def find_system(self, name: Optional[str] = None, host: Optional[str] = None) -> Optional[Dict]:
        systems = self.list_systems()
        if host:
            for sys in systems:
                if sys.get('host', '').lower() == host.lower():
                    return sys
        if name:
            for sys in systems:
                if sys.get('name', '').lower() == name.lower():
                    return sys
            for sys in systems:
                if name.lower() in sys.get('name', '').lower():
                    Logger.info(f"模糊匹配到系统: {sys['name']}")
                    return sys
        return None

    def get_latest_stats(self, system_id: str) -> Optional[Dict]:
        params = {'filter': f"system='{system_id}'", 'sort': '-created', 'perPage': 1}
        data = self._request('GET', '/api/collections/system_stats/records', params=params)
        items = data.get('items', [])
        if not items:
            return None
        return items[0].get('stats', {})


# ==================== StreamDock Action ====================
class NasMonitorAction(Action):
    def __init__(self, action: str, context: str, settings: Dict, plugin):
        super().__init__(action, context, settings, plugin)
        Logger.info(f"NasMonitorAction 初始化: context={context}")
        self._timer_uuid = f"nas_monitor_{context}"
        self._client: Optional[BeszelClient] = None
        self._system_id: Optional[str] = None
        self._refresh_interval = 10
        self._metric = 'cpu'
        self._ball_scale = 0.9
        self._bg_image: Optional[Image.Image] = None
        self._bg_image_path: str = ''
        self._first_refresh_done = False   # 标记首次刷新是否成功

        self._update_from_settings(settings)
        self._start_timer()

    def _update_from_settings(self, settings: Dict):
        Logger.info(f"更新设置: {settings}")
        url = settings.get('beszel_url', '').strip()
        email = settings.get('beszel_email', '').strip()
        password = settings.get('beszel_password', '').strip()
        agent = settings.get('beszel_agent', '').strip()

        try:
            interval = int(settings.get('refresh_interval', 10))
            self._refresh_interval = max(5, interval)
        except:
            self._refresh_interval = 10

        self._metric = settings.get('metric', 'cpu').strip().lower()
        if self._metric not in ['cpu', 'mp', 'dp', 's', 'gpu_pct']:
            self._metric = 'cpu'

        try:
            scale = float(settings.get('ball_scale', 0.9))
            self._ball_scale = max(0.4, min(1.5, scale))
        except:
            self._ball_scale = 0.9

        bg_path = settings.get('bg_image', '').strip()
        if bg_path != self._bg_image_path:
            self._bg_image_path = bg_path
            self._bg_image = None
            if bg_path:
                if not os.path.isabs(bg_path):
                    base_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.getcwd()
                    bg_path = os.path.join(base_dir, bg_path)
                try:
                    self._bg_image = Image.open(bg_path)
                    Logger.info(f"加载背景图片成功: {bg_path}")
                except Exception as e:
                    Logger.error(f"加载背景图片失败: {e}")

        if url and email and password and agent:
            try:
                self._client = BeszelClient(url, email, password)
                system = self._client.find_system(name=agent)
                if system:
                    self._system_id = system['id']
                    Logger.info(f"Beszel 初始化成功，系统ID: {self._system_id}")
                else:
                    Logger.error(f"未找到 Agent: {agent}")
                    self._system_id = None
            except Exception as e:
                Logger.error(f"Beszel 初始化失败: {e}")
                self._client = None
                self._system_id = None
        else:
            self._client = None
            self._system_id = None

        # 立即尝试刷新（重置标记）
        self._first_refresh_done = False
        self._refresh_data()

    def _start_timer(self):
        self.plugin.timer.clear_interval(self._timer_uuid)
        self.plugin.timer.set_interval(self._timer_uuid, self._refresh_interval * 1000, self._refresh_data)

    def _refresh_data(self):
        """拉取数据并更新按钮图片（失败时不覆盖已有图片）"""
        if not self._client or not self._system_id:
            # 首次未配置时显示提示，但不覆盖已有图片
            if not self._first_refresh_done:
                self.set_title("❌ 未配置")
            return

        try:
            stats = self._client.get_latest_stats(self._system_id)
            if not stats:
                Logger.warning("获取统计数据为空")
                # 无数据时不修改界面
                return

            # 生成悬浮球图片
            img = generate_float_ball(
                stats,
                size=(100, 100),
                metric=self._metric,
                background=self._bg_image,
                ball_scale=self._ball_scale
            )

            # 转换为 Base64 data URI
            buffer = BytesIO()
            img.save(buffer, format="PNG")
            b64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
            data_uri = f"data:image/png;base64,{b64}"

            # 设置按钮图片
            self.set_image(data_uri)
            # **关键修复**：清空标题，只显示图片
            self.set_title("")
            self._first_refresh_done = True

        except Exception as e:
            Logger.error(f"刷新数据失败: {e}")
            # 失败时不覆盖图片，仅当从未成功显示时显示错误
            if not self._first_refresh_done:
                self.set_title("⚠️ 错误")

    # ---------- 事件处理 ----------
    def on_did_receive_settings(self, settings: Dict):
        Logger.info(f"收到设置更新: {settings}")
        self._update_from_settings(settings)
        self._start_timer()

    def on_will_disappear(self):
        Logger.info("按钮消失，清除定时器")
        self.plugin.timer.clear_interval(self._timer_uuid)

    def on_key_down(self, payload: Dict):
        Logger.info("按钮按下，手动刷新")
        self._refresh_data()

    def on_property_inspector_did_appear(self, payload: Dict):
        Logger.info("属性面板打开，发送当前设置")
        self.send_to_property_inspector({
            'settings': self.settings
        })

    def on_send_to_plugin(self, payload: Dict):
        Logger.info(f"收到来自 PI 的消息: {payload}")
        command = payload.get('command')

        if command == 'refresh':
            self._refresh_data()
            self.send_to_property_inspector({'status': '已刷新'})
            return

        if command == 'getSettings':
            self.send_to_property_inspector({'settings': self.settings})
            return

        # 保存设置（若包含配置字段）
        if any(key in payload for key in ['beszel_url', 'beszel_email', 'beszel_password', 'beszel_agent']):
            self.set_settings(payload)
            self.send_to_property_inspector({'status': '设置已保存'})
        else:
            Logger.warning(f"未知的 PI 消息: {payload}")
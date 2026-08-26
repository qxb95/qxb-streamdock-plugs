import os
import sys
import ssl
import socket
import re
import datetime
import time
import base64
import io
import json
from PIL import Image, ImageDraw, ImageFont
from src.core.action import Action
from src.core.logger import Logger

TEST_DOMAIN = "example.com"

def get_resource_path(relative_path):
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base_path, relative_path)

# ---------- WHOIS/SSL 查询 ----------
SERVER_MAP = {
    'com': 'whois.verisign-grs.com',
    'net': 'whois.verisign-grs.com',
    'org': 'whois.publicinterestregistry.org',
    'cn': 'whois.cnnic.cn',
    'cc': 'whois.nic.cc',
    'tv': 'whois.nic.tv',
    'info': 'whois.afilias.net',
    'biz': 'whois.neulevel.biz',
    'xyz': 'whois.nic.xyz',
    'site': 'whois.nic.site',
    'top': 'whois.nic.top',
    'club': 'whois.nic.club',
    'online': 'whois.nic.online',
}

def query_whois(domain, server, port=43, timeout=15):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect((server, port))
        sock.send((domain + '\r\n').encode())
        response = b''
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                break
            response += chunk
        sock.close()
        return response.decode('utf-8', errors='ignore')
    except Exception as e:
        Logger.error(f"WHOIS 查询失败 ({server}): {e}")
        return None

def extract_expiry_date(text):
    patterns = [
        r'Registry Expiry Date:\s*([\d-]+(?:T[\d:]+Z)?)',
        r'Expiration Date:\s*([\d-]+(?:T[\d:]+Z)?)',
        r'expires:\s*([\d-]+(?:T[\d:]+Z)?)',
        r'Expiry date:\s*([\d-]+(?:T[\d:]+Z)?)',
        r'expire-date:\s*([\d-]+(?:T[\d:]+Z)?)',
        r'Valid Until:\s*([\d-]+)',
        r'paid-till:\s*([\d-]+)',
    ]
    for pat in patterns:
        match = re.search(pat, text, re.IGNORECASE)
        if match:
            dt_str = match.group(1).strip()
            if 'T' in dt_str:
                dt_str = dt_str.split('T')[0]
            try:
                return datetime.datetime.strptime(dt_str, '%Y-%m-%d')
            except:
                continue
    return None

def get_domain_expiry_days(domain):
    tld = domain.split('.')[-1].lower()
    primary_server = SERVER_MAP.get(tld, 'whois.iana.org')
    response = query_whois(domain, primary_server)
    if not response:
        return None
    if re.search(r'No match|Not found|no entries found|Status: free', response, re.IGNORECASE):
        Logger.info(f"域名 {domain} 未注册或已过期")
        return None
    if primary_server == 'whois.iana.org':
        refer_match = re.search(r'refer:\s*(\S+)', response, re.IGNORECASE)
        if refer_match:
            refer_server = refer_match.group(1).strip()
            Logger.info(f"IANA 指向授权服务器 {refer_server}，重新查询...")
            response = query_whois(domain, refer_server)
            if not response:
                return None
            if re.search(r'No match|Not found|no entries found|Status: free', response, re.IGNORECASE):
                Logger.info(f"域名 {domain} 未注册或已过期")
                return None
    expiry_dt = extract_expiry_date(response)
    if expiry_dt:
        now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
        days = (expiry_dt - now).days
        if days < -3650 or days > 3650:
            Logger.warning(f"计算的天数 {days} 异常，可能提取了错误日期")
            return None
        return days
    else:
        Logger.warning(f"未在 WHOIS 响应中找到到期日期")
        return None

def get_ssl_expiry_days(domain):
    try:
        context = ssl.create_default_context()
        with socket.create_connection((domain, 443), timeout=10) as sock:
            with context.wrap_socket(sock, server_hostname=domain) as ssock:
                cert = ssock.getpeercert()
        expire_date = datetime.datetime.strptime(cert['notAfter'], '%b %d %H:%M:%S %Y %Z')
        now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
        return (expire_date - now).days
    except Exception as e:
        Logger.error(f"SSL 查询失败: {e}")
        return None

# ---------- 图片生成 ----------
def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def get_system_font(size):
    font_paths = [
        "C:/Windows/Fonts/simhei.ttf",
        "C:/Windows/Fonts/msyh.ttc",
        "/System/Library/Fonts/PingFang.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for path in font_paths:
        try:
            return ImageFont.truetype(path, size)
        except:
            continue
    Logger.warning("未找到可缩放字体，使用默认字体")
    return ImageFont.load_default()

def generate_button_image(domain, ssl_text, dom_text, ssl_color_rgb, dom_color_rgb,
                          ssl_font_size=18, dom_font_size=18,
                          domain_font_size=12, domain_color_rgb=(255,255,255),
                          domain_position='bottom', show_domain=True,
                          bg_path="background.png", plugin_root=None):
    width, height = 200, 200
    if plugin_root and not os.path.isabs(bg_path):
        bg_path = os.path.join(plugin_root, bg_path)
    try:
        bg = Image.open(bg_path).convert("RGB")
        bg = bg.resize((width, height), Image.Resampling.LANCZOS)
        img = bg.copy()
    except Exception as e:
        Logger.warning(f"背景图片加载失败 ({bg_path}): {e}，使用深色背景")
        img = Image.new('RGB', (width, height), color=(30, 30, 30))
    draw = ImageDraw.Draw(img)

    font_ssl = get_system_font(ssl_font_size)
    font_dom = get_system_font(dom_font_size)
    font_domain = get_system_font(domain_font_size)

    # 计算 SSL 和 DOM 的尺寸
    ssl_bbox = draw.textbbox((0, 0), ssl_text, font=font_ssl)
    dom_bbox = draw.textbbox((0, 0), dom_text, font=font_dom)
    ssl_w = ssl_bbox[2] - ssl_bbox[0]
    ssl_h = ssl_bbox[3] - ssl_bbox[1]
    dom_w = dom_bbox[2] - dom_bbox[0]
    dom_h = dom_bbox[3] - dom_bbox[1]
    max_w = max(ssl_w, dom_w)
    total_h = ssl_h + dom_h + 8

    if show_domain:
        domain_bbox = draw.textbbox((0, 0), domain, font=font_domain)
        dom_w = domain_bbox[2] - domain_bbox[0]
        dom_h = domain_bbox[3] - domain_bbox[1]
        margin = domain_font_size
    else:
        dom_w = dom_h = 0
        margin = 0

    # 根据域名位置计算 SSL/DOM 的整体起始 y
    if show_domain and domain_position == 'top':
        y_domain = margin
        available_start = y_domain + dom_h + margin
        available_height = height - available_start - margin
        y_ssl = available_start + (available_height - total_h) // 2
    elif show_domain and domain_position == 'bottom':
        y_domain = height - dom_h - margin
        available_start = margin
        available_height = y_domain - available_start - margin
        y_ssl = available_start + (available_height - total_h) // 2
    elif show_domain and domain_position == 'center':
        y_domain = (height - dom_h - total_h - margin) // 2
        y_ssl = y_domain + dom_h + margin
        if y_ssl + total_h > height:
            y_ssl = height - total_h - margin
    else:
        y_ssl = (height - total_h) // 2
        y_domain = 0

    if y_ssl < margin:
        y_ssl = margin
    if y_ssl + total_h > height - margin:
        y_ssl = height - total_h - margin

    if show_domain:
        x_domain = (width - dom_w) // 2
        draw.text((x_domain, y_domain), domain, fill=domain_color_rgb, font=font_domain)

    x_start = (width - max_w) // 2
    draw.text((x_start, y_ssl), ssl_text, fill=ssl_color_rgb, font=font_ssl)
    draw.text((x_start, y_ssl + ssl_h + 8), dom_text, fill=dom_color_rgb, font=font_dom)

    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
    return f"data:image/png;base64,{img_base64}"

# ---------- 颜色区间计算 ----------
def get_color_for_days(days, threshold, color_good, color_warn, color_bad):
    if days is None:
        return hex_to_rgb(color_good)
    if days < 0:
        return hex_to_rgb(color_bad)
    elif days < threshold:
        return hex_to_rgb(color_warn)
    else:
        return hex_to_rgb(color_good)

# ---------- StreamDock Action ----------
class CertMonitor(Action):
    _cache = {}
    CACHE_TTL = 10800

    def __init__(self, action: str, context: str, settings: dict, plugin):
        super().__init__(action, context, settings, plugin)
        self.plugin_root = get_resource_path('')

        domains_str = settings.get('domains', '')
        self.domains = [d.strip() for d in domains_str.split(',') if d.strip()]
        if not self.domains:
            Logger.warning(f"[CertMonitor] 未从设置获取域名，使用测试域名 {TEST_DOMAIN}")
            self.domains = [TEST_DOMAIN]
        else:
            Logger.info(f"[CertMonitor] 加载域名列表: {self.domains}")

        self.current_index = 0
        self.ssl_threshold = settings.get('ssl_threshold', 30)
        self.domain_threshold = settings.get('domain_threshold', 30)
        self.update_interval = settings.get('update_interval', 21600000)
        self.bg_path = settings.get('background_path', 'background.png')
        self.ssl_font_size = settings.get('ssl_font_size', 18)
        self.dom_font_size = settings.get('dom_font_size', 18)
        self.font_bold = settings.get('font_bold', True)

        self.domain_font_size = settings.get('domain_font_size', 12)
        self.domain_color = settings.get('domain_color', '#ffffff')
        self.domain_position = settings.get('domain_position', 'bottom')
        self.show_domain = settings.get('show_domain', True)

        self.ssl_color_good = settings.get('ssl_color_good', '#00ff00')
        self.ssl_color_warn = settings.get('ssl_color_warn', '#ffa500')
        self.ssl_color_bad = settings.get('ssl_color_bad', '#ff0000')
        self.dom_color_good = settings.get('dom_color_good', '#00ff00')
        self.dom_color_warn = settings.get('dom_color_warn', '#ffa500')
        self.dom_color_bad = settings.get('dom_color_bad', '#ff0000')

        Logger.info(f"[CertMonitor] 初始化完成，共 {len(self.domains)} 个域名")
        self._schedule_update()

    @classmethod
    def _get_cached(cls, domain, query_type):
        key = (domain, query_type)
        now = time.time()
        if key in cls._cache:
            entry = cls._cache[key]
            if now - entry['timestamp'] < cls.CACHE_TTL:
                Logger.debug(f"Cache hit for {domain} ({query_type})")
                return entry['value']
        Logger.debug(f"Cache miss for {domain} ({query_type}), querying...")
        if query_type == 'ssl':
            value = get_ssl_expiry_days(domain)
        else:
            value = get_domain_expiry_days(domain)
        cls._cache[key] = {'value': value, 'timestamp': now}
        return value

    def _schedule_update(self):
        timer_id = f"cert_monitor_{self.context}"
        self.plugin.timer.clear_interval(timer_id)
        self.plugin.timer.set_interval(
            timer_id,
            self.update_interval,
            lambda: self._update_info()
        )
        self._update_info()

    def _update_info(self):
        if not self.domains:
            self.set_title("无域名")
            Logger.warning("[CertMonitor] 域名列表为空")
            return

        domain = self.domains[self.current_index]
        Logger.info(f"[CertMonitor] 正在更新域名: {domain}")

        self.set_title("")

        ssl_days = self._get_cached(domain, 'ssl')
        domain_days = self._get_cached(domain, 'domain')

        ssl_text = f"SSL: {ssl_days if ssl_days is not None else 'N/A'}天"
        dom_text = f"DOM: {domain_days if domain_days is not None else 'N/A'}天"

        ssl_color_rgb = get_color_for_days(ssl_days, self.ssl_threshold,
                                           self.ssl_color_good, self.ssl_color_warn, self.ssl_color_bad)
        dom_color_rgb = get_color_for_days(domain_days, self.domain_threshold,
                                           self.dom_color_good, self.dom_color_warn, self.dom_color_bad)
        domain_color_rgb = hex_to_rgb(self.domain_color)

        img_data = generate_button_image(
            domain, ssl_text, dom_text,
            ssl_color_rgb, dom_color_rgb,
            ssl_font_size=self.ssl_font_size,
            dom_font_size=self.dom_font_size,
            domain_font_size=self.domain_font_size,
            domain_color_rgb=domain_color_rgb,
            domain_position=self.domain_position,
            show_domain=self.show_domain,
            bg_path=self.bg_path,
            plugin_root=self.plugin_root
        )
        self.set_image(img_data)

        if (ssl_days is not None and ssl_days < self.ssl_threshold) or \
           (domain_days is not None and domain_days < self.domain_threshold):
            self.set_state(1)
        else:
            self.set_state(0)

        Logger.info(f"[CertMonitor] 更新完成: SSL={ssl_days}, DOM={domain_days}")

    def on_key_down(self, payload: dict):
        if not self.domains:
            self.show_alert()
            return
        self.current_index = (self.current_index + 1) % len(self.domains)
        self._update_info()
        # 取消显示对号
        # self.show_ok()
        Logger.info(f"[CertMonitor] 翻页到 {self.current_index+1}/{len(self.domains)}")

    def on_key_up(self, payload: dict):
        pass

    def on_did_receive_settings(self, settings: dict):
        Logger.info(f"[CertMonitor] 收到设置更新: {settings}")
        domains_str = settings.get('domains', '')
        new_domains = [d.strip() for d in domains_str.split(',') if d.strip()]
        if new_domains:
            self.domains = new_domains
        else:
            self.domains = [TEST_DOMAIN]
            Logger.warning("[CertMonitor] 设置清空域名，使用测试域名")

        self.ssl_threshold = settings.get('ssl_threshold', 30)
        self.domain_threshold = settings.get('domain_threshold', 30)
        self.update_interval = settings.get('update_interval', 21600000)
        self.bg_path = settings.get('background_path', 'background.png')
        self.ssl_font_size = settings.get('ssl_font_size', 18)
        self.dom_font_size = settings.get('dom_font_size', 18)
        self.font_bold = settings.get('font_bold', True)

        self.domain_font_size = settings.get('domain_font_size', 12)
        self.domain_color = settings.get('domain_color', '#ffffff')
        self.domain_position = settings.get('domain_position', 'bottom')
        self.show_domain = settings.get('show_domain', True)

        self.ssl_color_good = settings.get('ssl_color_good', '#00ff00')
        self.ssl_color_warn = settings.get('ssl_color_warn', '#ffa500')
        self.ssl_color_bad = settings.get('ssl_color_bad', '#ff0000')
        self.dom_color_good = settings.get('dom_color_good', '#00ff00')
        self.dom_color_warn = settings.get('dom_color_warn', '#ffa500')
        self.dom_color_bad = settings.get('dom_color_bad', '#ff0000')

        self.current_index = 0
        self._schedule_update()
        Logger.info(f"[CertMonitor] 设置已更新，当前域名列表: {self.domains}")

    def on_send_to_plugin(self, payload: dict):
        Logger.info(f"[CertMonitor] 收到 sendToPlugin: {payload}")
        if isinstance(payload, dict) and 'domains' in payload:
            self.on_did_receive_settings(payload)

    def on_will_disappear(self):
        self.plugin.timer.clear_interval(f"cert_monitor_{self.context}")
        Logger.info(f"[CertMonitor] 清理定时器")
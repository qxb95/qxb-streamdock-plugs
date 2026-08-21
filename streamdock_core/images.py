"""按键图像相关工具：base64 data URL 编码与字体加载。"""
import base64
import io
from typing import Optional

from PIL import Image, ImageDraw, ImageFont

from .logger import Logger

#: 常见的中文/英文字体候选路径，供 load_font 使用
DEFAULT_FONT_CANDIDATES = (
    'C:/Windows/Fonts/msyh.ttc',
    'C:/Windows/Fonts/arial.ttf',
    'arial.ttf',
    '/System/Library/Fonts/PingFang.ttc',
    '/System/Library/Fonts/Helvetica.ttc',
    '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
)


def to_data_url(image: Image.Image, image_format: str = 'PNG') -> str:
    """将 PIL 图像编码为 StreamDock setImage 需要的 data URL"""
    buffered = io.BytesIO()
    image.save(buffered, format=image_format)
    encoded = base64.b64encode(buffered.getvalue()).decode('utf-8')
    return f"data:image/{image_format.lower()};base64,{encoded}"


def load_font(size: int, *candidates: str) -> ImageFont.ImageFont:
    """按候选顺序加载 TrueType 字体，全部失败时回退到 PIL 默认字体

    Args:
        size: 字号
        *candidates: 优先尝试的字体路径，未提供时使用 DEFAULT_FONT_CANDIDATES
    """
    paths = candidates or DEFAULT_FONT_CANDIDATES
    for path in paths:
        if not path:
            continue
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    Logger.warning(f"未找到可用字体，使用默认字体: {paths}")
    return ImageFont.load_default()


def text_width(text: str, font: Optional[ImageFont.ImageFont] = None) -> int:
    """测量文本宽度（像素）"""
    draw = ImageDraw.Draw(Image.new('RGB', (1, 1)))
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0]

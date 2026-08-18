# src/actions/time.py
import io
import base64
from src.core.action import Action
from src.core.logger import Logger
from src.core.renderer import render_clock


class Time(Action):
    """
    时钟 Action：在 StreamDock 按键上显示模拟指针表盘。
    每秒自动刷新，点击按键可手动刷新。
    """

    def __init__(self, action: str, context: str, settings: dict, plugin):
        super().__init__(action, context, settings, plugin)
        self.canvas_size = 500
        self.dial_size = 400
        self._timer_key = f"time_update_{context}"

        # 立即发送一张表盘图片（确保按键出现时即显示）
        try:
            img = render_clock(self.canvas_size, self.dial_size)
            buffered = io.BytesIO()
            img.save(buffered, format="PNG")
            img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
            self.set_image(f"data:image/png;base64,{img_base64}")
            Logger.info("[Time] ✅ 初始图片已发送")
        except Exception as e:
            Logger.error(f"[Time] ❌ 初始图片发送失败: {e}")

        # 启动定时器：每秒刷新一次
        self.plugin.timer.set_interval(
            self._timer_key,
            1000,  # 1000ms = 1 秒
            self._on_timer_tick
        )
        Logger.info(f"[Time] 已初始化, context={context}")

    def _on_timer_tick(self):
        """定时器回调：刷新表盘图片"""
        try:
            img = render_clock(self.canvas_size, self.dial_size)
            buffered = io.BytesIO()
            img.save(buffered, format="PNG")
            img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
            self.set_image(f"data:image/png;base64,{img_base64}")
            Logger.info("[Time] ✅ 定时刷新图片已发送")
        except Exception as e:
            Logger.error(f"[Time] ❌ 定时刷新失败: {e}")

    def on_will_disappear(self):
        """按键消失时清理定时器"""
        self.plugin.timer.clear_interval(self._timer_key)
        Logger.info(f"[Time] 已销毁, context={self.context}")

    def on_key_up(self, payload: dict):
        """点击按键时手动刷新一次（便于调试）"""
        Logger.info(f"[Time] 按键点击: {payload}")
        self._on_timer_tick()
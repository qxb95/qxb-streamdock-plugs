# src/actions/time.py
from streamdock_core import Action, Logger
from streamdock_core.images import to_data_url

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
        self._refresh()

        # 启动定时器：每秒刷新一次
        self.plugin.timer.set_interval(
            self._timer_key,
            1000,  # 1000ms = 1 秒
            self._refresh
        )
        Logger.info(f"[Time] 已初始化, context={context}")

    def _refresh(self):
        """渲染并发送一张最新的表盘图片"""
        try:
            self.set_image(to_data_url(render_clock(self.canvas_size, self.dial_size)))
        except Exception as e:
            Logger.error(f"[Time] 表盘刷新失败: {e}")

    def on_will_disappear(self):
        """按键消失时清理定时器"""
        self.plugin.timer.clear_interval(self._timer_key)
        Logger.info(f"[Time] 已销毁, context={self.context}")

    def on_key_up(self, payload: dict):
        """点击按键时手动刷新一次（便于调试）"""
        Logger.info(f"[Time] 按键点击: {payload}")
        self._refresh()

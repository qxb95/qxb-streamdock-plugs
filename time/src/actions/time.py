# src/actions/time.py
<<<<<<< HEAD
import io
import base64
=======
import json
import time
import io
import base64
import os
>>>>>>> origin/main
from src.core.action import Action
from src.core.logger import Logger
from src.core.renderer import render_clock


class Time(Action):
<<<<<<< HEAD
    """
    时钟 Action：在 StreamDock 按键上显示模拟指针表盘。
    每秒自动刷新，点击按键可手动刷新。
    """

=======
>>>>>>> origin/main
    def __init__(self, action: str, context: str, settings: dict, plugin):
        super().__init__(action, context, settings, plugin)
        self.canvas_size = 500
        self.dial_size = 400
<<<<<<< HEAD
        self._timer_key = f"time_update_{context}"

        # 立即发送一张表盘图片（确保按键出现时即显示）
=======
        self._frame_count = 0

        os.makedirs("debug_output", exist_ok=True)

        # 立即发送测试图片
>>>>>>> origin/main
        try:
            img = render_clock(self.canvas_size, self.dial_size)
            buffered = io.BytesIO()
            img.save(buffered, format="PNG")
            img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
            self.set_image(f"data:image/png;base64,{img_base64}")
<<<<<<< HEAD
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
=======
            Logger.info("[Time] ✅ 测试图片已立即发送")
        except Exception as e:
            Logger.error(f"[Time] ❌ 发送测试图片失败: {e}")

        # 设置定时器（1000ms = 1秒）
        self.plugin.timer.set_interval(
            f'time_update_{context}',
            1000,
            self._on_timer_tick
        )
        Logger.info(f"[Time] 已初始化, canvas={self.canvas_size}, dial={self.dial_size}, context={context}")

    def _on_timer_tick(self):
        try:
            img = render_clock(self.canvas_size, self.dial_size)
            self._frame_count += 1
            # 保存到调试目录（可选）
            filename = f"debug_output/clock_{self._frame_count:04d}.png"
            img.save(filename)

>>>>>>> origin/main
            buffered = io.BytesIO()
            img.save(buffered, format="PNG")
            img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
            self.set_image(f"data:image/png;base64,{img_base64}")
            Logger.info("[Time] ✅ 定时刷新图片已发送")
        except Exception as e:
            Logger.error(f"[Time] ❌ 定时刷新失败: {e}")

    def on_will_disappear(self):
<<<<<<< HEAD
        """按键消失时清理定时器"""
        self.plugin.timer.clear_interval(self._timer_key)
        Logger.info(f"[Time] 已销毁, context={self.context}")

    def on_key_up(self, payload: dict):
        """点击按键时手动刷新一次（便于调试）"""
=======
        self.plugin.timer.clear_interval(f'time_update_{self.context}')
        Logger.info(f"[Time] 已销毁, context={self.context}")

    def on_key_up(self, payload: dict):
>>>>>>> origin/main
        Logger.info(f"[Time] 按键点击: {payload}")
        self._on_timer_tick()
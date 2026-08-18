# src/actions/time.py
import json
import time
import io
import base64
import os
from src.core.action import Action
from src.core.logger import Logger
from src.core.renderer import render_clock


class Time(Action):
    def __init__(self, action: str, context: str, settings: dict, plugin):
        super().__init__(action, context, settings, plugin)
        self.canvas_size = 500
        self.dial_size = 400
        self._frame_count = 0

        os.makedirs("debug_output", exist_ok=True)

        # 立即发送测试图片
        try:
            img = render_clock(self.canvas_size, self.dial_size)
            buffered = io.BytesIO()
            img.save(buffered, format="PNG")
            img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
            self.set_image(f"data:image/png;base64,{img_base64}")
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

            buffered = io.BytesIO()
            img.save(buffered, format="PNG")
            img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
            self.set_image(f"data:image/png;base64,{img_base64}")
            Logger.info("[Time] ✅ 定时刷新图片已发送")
        except Exception as e:
            Logger.error(f"[Time] ❌ 定时刷新失败: {e}")

    def on_will_disappear(self):
        self.plugin.timer.clear_interval(f'time_update_{self.context}')
        Logger.info(f"[Time] 已销毁, context={self.context}")

    def on_key_up(self, payload: dict):
        Logger.info(f"[Time] 按键点击: {payload}")
        self._on_timer_tick()
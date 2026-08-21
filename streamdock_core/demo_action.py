"""演示用 Action：调用一遍常用的 StreamDock 接口，便于验证 SDK 是否工作。"""
from PIL import Image, ImageDraw

from .action import Action
from .images import to_data_url
from .logger import Logger


class Custom(Action):
    def __init__(self, action: str, context: str, settings: dict, plugin):
        super().__init__(action, context, settings, plugin)
        self.plugin.set_global_settings({"test": "test"})

        # 生成示例图片
        img = Image.new('RGB', (200, 200), color='white')
        draw = ImageDraw.Draw(img)
        draw.rectangle((50, 50, 150, 150), outline='blue', width=3)
        draw.text((60, 60), "Hello", fill='black')
        self.set_image(to_data_url(img))

        self.set_settings({"test": "test"})
        self.log_message("---------------test--------------")
        self.set_title("test")
        self.show_alert()
        Logger.info(f"[Custom] Initialized with context {context}")

    def on_will_disappear(self):
        self.plugin.timer.clear_interval(f'time_update_{self.context}')
        Logger.info(f"[Custom] Will disappear for context {self.context}")

    def on_did_receive_global_settings(self, settings: dict):
        Logger.info(f"[Custom] Received global settings: {settings}")

    def on_key_down(self, payload: dict):
        Logger.info(f"[Custom] Key down event with payload: {payload}")

    def on_key_up(self, payload: dict):
        self.plugin.set_global_settings({"test": "tedasdasdst"})
        self.set_settings({"test": "dasdsada"})
        self.send_to_property_inspector({"test": "asdas"})
        self.open_url("https://sdk.key123.vip/guide/get-started.html")
        self.show_ok()
        Logger.info(f"[Custom] Key up event with payload: {payload}")

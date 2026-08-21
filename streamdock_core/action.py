import json
from typing import Any, Dict

from .logger import Logger


class Action:
    """Action 基类，对应 StreamDock 界面上的一个按键

    子类可按需实现 on_key_down / on_will_disappear 等事件回调，
    并使用 set_title / set_image 等方法向 StreamDock 发送指令。
    """

    def __init__(self, action: str, context: str, settings: Dict, plugin):
        self.action = action
        self.context = context
        self.settings = settings
        self.title = ""
        self.title_parameters = {}
        self._server = plugin.ws
        self.plugin = plugin

    # ---------- 事件回调默认实现，子类可按需覆盖 ----------
    def on_will_appear(self):
        pass

    def on_will_disappear(self):
        pass

    def on_key_down(self, payload: Dict):
        pass

    def on_key_up(self, payload: Dict):
        pass

    def on_dial_down(self, payload: Dict):
        pass

    def on_dial_up(self, payload: Dict):
        pass

    def on_dial_rotate(self, payload: Dict):
        pass

    def on_did_receive_settings(self, settings: Dict):
        self.settings = settings

    def on_title_parameters_did_change(self, payload: Dict):
        self.title = payload.get('title', '')
        self.title_parameters = payload.get('titleParameters', {})

    def on_property_inspector_did_appear(self, data: Dict):
        pass

    def on_property_inspector_did_disappear(self, data: Dict):
        pass

    def on_send_to_plugin(self, payload: Dict):
        pass

    def on_did_receive_global_settings(self, settings: Any):
        pass

    def on_device_did_connect(self, data: Dict):
        pass

    def on_device_did_disconnect(self, data: Dict):
        pass

    def on_application_did_launch(self, data: Dict):
        pass

    def on_application_did_terminate(self, data: Dict):
        pass

    def on_system_did_wake_up(self, data: Dict):
        pass

    # ---------- 发送指令 ----------
    def _send(self, event: str, **fields: Any):
        """向 StreamDock 发送一条事件消息

        Args:
            event: 事件名称，如 setTitle
            **fields: 事件的其余字段，如 context / payload
        """
        if not self._server:
            return
        try:
            self._server.send(json.dumps({'event': event, **fields}))
        except Exception as e:
            Logger.error(f"发送 {event} 失败: {e}")

    def send_to_property_inspector(self, payload: Any):
        self._send('sendToPropertyInspector', action=self.action, context=self.context, payload=payload)

    def set_state(self, state: int):
        self._send('setState', context=self.context, payload={'state': state})

    def set_title(self, title: str):
        self._send('setTitle', context=self.context, payload={'title': title, 'target': 0})

    def set_settings(self, payload: Any):
        self.settings = payload
        self._send('setSettings', context=self.context, payload=payload)

    def open_url(self, url: str):
        self._send('openUrl', payload={'url': url})

    def show_ok(self):
        self._send('showOk', context=self.context)

    def show_alert(self):
        self._send('showAlert', context=self.context)

    def set_image(self, url: str):
        self._send('setImage', context=self.context, payload={'target': 0, 'image': url})

    def log_message(self, message: str):
        self._send('logMessage', payload={'message': message})

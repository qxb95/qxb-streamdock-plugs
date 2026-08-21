import json
from typing import Any, Dict

from .logger import Logger


class Action:
    def __init__(self, action: str, context: str, settings: Dict, plugin):
        self.action = action
        self.context = context
        self.settings = settings
        self.title = ""
        self.title_parameters = {}
        self._server = plugin.ws
        self.plugin = plugin

    def send_to_property_inspector(self, payload: Any):
        if self._server:
            self._server.send(json.dumps({
                'event': 'sendToPropertyInspector',
                'action': self.action,
                'context': self.context,
                'payload': payload
            }))

    def set_state(self, state: int):
        if self._server:
            self._server.send(json.dumps({
                'event': 'setState',
                'context': self.context,
                'payload': {'state': state}
            }))

    def set_title(self, title: str):
        if self._server:
            self._server.send(json.dumps({
                'event': 'setTitle',
                'context': self.context,
                'payload': {'title': title, 'target': 0}
            }))

    def set_settings(self, payload: Any):
        if self._server:
            self.settings = payload
            self._server.send(json.dumps({
                'event': 'setSettings',
                'context': self.context,
                'payload': payload
            }))

    def open_url(self, url: str):
        if self._server:
            self._server.send(json.dumps({
                'event': 'openUrl',
                'payload': {'url': url}
            }))

    def show_ok(self):
        if self._server:
            self._server.send(json.dumps({
                'event': 'showOk',
                'context': self.context
            }))

    def show_alert(self):
        if self._server:
            self._server.send(json.dumps({
                'event': 'showAlert',
                'context': self.context
            }))

    def set_image(self, url: str):
        if self._server:
            try:
                message = json.dumps({
                    'event': 'setImage',
                    'context': self.context,
                    'payload': {'target': 0, 'image': url}
                })
                self._server.send(message)
            except Exception as e:
                Logger.error(f"发送 setImage 失败 (context={self.context}): {e}")

    def log_message(self, message: str):
        if self._server:
            self._server.send(json.dumps({
                'event': 'logMessage',
                'payload': {'message': message}
            }))
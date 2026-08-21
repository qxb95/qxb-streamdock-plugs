# src/core/plugin.py
import json
import threading
import time
import traceback
import websocket
from typing import Any, Dict, List, Optional
from .timer import Timer
from .action import Action
from .logger import Logger


class Plugin:
    def __init__(self, port: int, plugin_uuid: str, event: str, info: Dict[str, Any]):
        self.actions: Dict[str, Action] = {}
        self.global_settings: Any = None
        self.timer = Timer()
        self.plugin_uuid = plugin_uuid
        self._connected = False

        # 初始化 WebSocket
        self.ws = websocket.WebSocketApp(
            f'ws://127.0.0.1:{port}',
            on_open=lambda ws: self._on_open(ws, event, plugin_uuid),
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close
        )

        # 在后台线程运行 WebSocket
        self._ws_thread = threading.Thread(target=self.ws.run_forever, daemon=True)
        self._ws_thread.start()

        # ✅ 等待连接建立（最多 3 秒，超时后只记录警告，不抛异常）
        timeout = 3.0
        start = time.time()
        while not self._connected and (time.time() - start) < timeout:
            time.sleep(0.1)

        if not self._connected:
            Logger.warning("WebSocket 连接超时，将继续运行（可能未连接 StreamDock）")
        else:
            Logger.info("✅ WebSocket 连接已建立")

    def _on_open(self, ws, event: str, plugin_uuid: str):
        Logger.info("WebSocket connected")
        self._connected = True
        ws.send(json.dumps({'event': event, 'uuid': plugin_uuid}))
        Logger.info("已发送注册事件")

    def _on_error(self, ws, error):
        Logger.error(f"WebSocket error: {error}")
        self._connected = False

    def _on_close(self, ws, close_code, close_msg):
        Logger.info(f"WebSocket closed (code: {close_code})")
        self._connected = False

    def _on_message(self, ws, message):
        """处理从 StreamDock 接收到的消息"""
        try:
            data = json.loads(message)
        except json.JSONDecodeError as e:
            Logger.error(f"JSON 解析失败: {e}")
            return

        try:
            self._handle_event(data)
        except Exception:
            Logger.error(f"处理事件 '{data.get('event')}' 异常:\n{traceback.format_exc()}")

    def _handle_event(self, data):
        event = data.get('event')
        Logger.info(f"收到事件: {event}")

        # 全局设置
        if event == 'didReceiveGlobalSettings':
            self.global_settings = data.get('payload', {}).get('settings')
            for action in self.actions.values():
                if hasattr(action, 'on_did_receive_global_settings'):
                    action.on_did_receive_global_settings(self.global_settings)

        # 按键出现
        elif event == 'willAppear':
            context = data.get('context')
            if context and context not in self.actions:
                from .action_factory import ActionFactory
                action = ActionFactory.create_action(
                    data.get('action', ''),
                    context,
                    data.get('payload', {}).get('settings', {}),
                    self
                )
                if action:
                    self.actions[context] = action
                    if hasattr(action, 'on_will_appear'):
                        action.on_will_appear()
                else:
                    Logger.error(f"创建 Action 失败: context={context}")

        # 按键消失
        elif event == 'willDisappear':
            context = data.get('context')
            if context and context in self.actions:
                action = self.actions[context]
                if hasattr(action, 'on_will_disappear'):
                    action.on_will_disappear()
                del self.actions[context]

        # 设置更新
        elif event == 'didReceiveSettings':
            context = data.get('context')
            if context and context in self.actions:
                action = self.actions[context]
                settings = data.get('payload', {}).get('settings', {})
                if hasattr(action, 'on_did_receive_settings'):
                    action.on_did_receive_settings(settings)
                else:
                    action.settings = settings

        # 标题参数变更
        elif event == 'titleParametersDidChange':
            context = data.get('context')
            if context and context in self.actions:
                action = self.actions[context]
                payload = data.get('payload', {})
                if hasattr(action, 'on_title_parameters_did_change'):
                    action.on_title_parameters_did_change(payload)
                else:
                    action.title = payload.get('title', '')
                    action.title_parameters = payload.get('titleParameters', {})

        # 按键事件
        context_events = {
            'keyDown': 'on_key_down',
            'keyUp': 'on_key_up',
            'dialDown': 'on_dial_down',
            'dialUp': 'on_dial_up',
            'dialRotate': 'on_dial_rotate'
        }
        if event in context_events:
            context = data.get('context')
            if context and context in self.actions:
                action = self.actions[context]
                handler = context_events[event]
                if hasattr(action, handler):
                    getattr(action, handler)(data.get('payload', {}))

        # 全局事件
        global_events = {
            'deviceDidConnect': 'on_device_did_connect',
            'deviceDidDisconnect': 'on_device_did_disconnect',
            'applicationDidLaunch': 'on_application_did_launch',
            'applicationDidTerminate': 'on_application_did_terminate',
            'systemDidWakeUp': 'on_system_did_wake_up'
        }
        if event in global_events:
            handler = global_events[event]
            for action in self.actions.values():
                if hasattr(action, handler):
                    getattr(action, handler)(data)

        # 属性检查器
        elif event == 'propertyInspectorDidAppear':
            context = data.get('context')
            if context and context in self.actions:
                action = self.actions[context]
                if hasattr(action, 'on_property_inspector_did_appear'):
                    action.on_property_inspector_did_appear(data)

        elif event == 'propertyInspectorDidDisappear':
            context = data.get('context')
            if context and context in self.actions:
                action = self.actions[context]
                if hasattr(action, 'on_property_inspector_did_disappear'):
                    action.on_property_inspector_did_disappear(data)

        # 从属性检查器发送到插件
        elif event == 'sendToPlugin':
            context = data.get('context')
            if context and context in self.actions:
                action = self.actions[context]
                if hasattr(action, 'on_send_to_plugin'):
                    action.on_send_to_plugin(data.get('payload', {}))

    # ---------- 公开 API ----------
    def set_global_settings(self, payload: Any):
        if self.ws and self._connected:
            self.ws.send(json.dumps({
                'event': 'setGlobalSettings',
                'context': self.plugin_uuid,
                'payload': payload
            }))
            self.global_settings = payload

    def get_global_settings(self):
        if self.ws and self._connected:
            self.ws.send(json.dumps({
                'event': 'getGlobalSettings',
                'context': self.plugin_uuid
            }))

    def get_action(self, context: str) -> Optional[Action]:
        return self.actions.get(context)

    def get_actions(self, action: str) -> List[Action]:
        return [a for a in self.actions.values() if a.action == action]

    def stop(self):
        if self.ws:
            self.ws.close()
        Logger.info("Plugin stopped")
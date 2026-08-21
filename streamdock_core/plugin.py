import json
import threading
import time
import traceback
from typing import Any, Callable, Dict, List, Optional

import websocket

from .action import Action
from .action_factory import ActionFactory
from .logger import Logger
from .timer import Timer


Callback = Callable[[Action, Any], None]


def _payload(data: Dict[str, Any]) -> Any:
    return data.get('payload', {})


def _settings(data: Dict[str, Any]) -> Any:
    return data.get('payload', {}).get('settings', {})


def _message(data: Dict[str, Any]) -> Any:
    return data


#: 需要转发给单个 Action 的事件 -> (回调, 回调参数提取函数)
CONTEXT_EVENTS: Dict[str, tuple] = {
    'keyDown': (Action.on_key_down, _payload),
    'keyUp': (Action.on_key_up, _payload),
    'dialDown': (Action.on_dial_down, _payload),
    'dialUp': (Action.on_dial_up, _payload),
    'dialRotate': (Action.on_dial_rotate, _payload),
    'didReceiveSettings': (Action.on_did_receive_settings, _settings),
    'titleParametersDidChange': (Action.on_title_parameters_did_change, _payload),
    'propertyInspectorDidAppear': (Action.on_property_inspector_did_appear, _message),
    'propertyInspectorDidDisappear': (Action.on_property_inspector_did_disappear, _message),
    'sendToPlugin': (Action.on_send_to_plugin, _payload),
}

#: 需要广播给所有 Action 的事件 -> 回调
GLOBAL_EVENTS: Dict[str, Callback] = {
    'deviceDidConnect': Action.on_device_did_connect,
    'deviceDidDisconnect': Action.on_device_did_disconnect,
    'applicationDidLaunch': Action.on_application_did_launch,
    'applicationDidTerminate': Action.on_application_did_terminate,
    'systemDidWakeUp': Action.on_system_did_wake_up,
}

CONNECT_TIMEOUT = 3.0


class Plugin:
    """Stream Dock 插件的核心类，负责管理 WebSocket 连接和分发 Stream Dock 事件

    该类维护与 Stream Dock 软件的 WebSocket 连接，处理各种事件（如按键出现、消失、设置更改等），
    并管理插件的 Action 实例。每个 Action 实例对应 Stream Dock 界面上的一个按键。
    """

    def __init__(self, port: int, plugin_uuid: str, event: str, info: Dict[str, Any]):
        """初始化插件实例

        Args:
            port: WebSocket 服务器端口号
            plugin_uuid: 插件的唯一标识符
            event: 注册事件类型
            info: 包含 Stream Dock 与设备信息的对象
        """
        self.actions: Dict[str, Action] = {}
        self.global_settings: Any = None
        self.timer = Timer()
        self.plugin_uuid = plugin_uuid
        self.info = info
        self._connected = False

        self.ws = websocket.WebSocketApp(
            f'ws://127.0.0.1:{port}',
            on_open=lambda ws: self._on_open(ws, event, plugin_uuid),
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close
        )

        self._ws_thread = threading.Thread(target=self.ws.run_forever, daemon=True)
        self._ws_thread.start()

        # 等待连接建立，超时后只记录警告，不抛异常
        start = time.time()
        while not self._connected and (time.time() - start) < CONNECT_TIMEOUT:
            time.sleep(0.1)
        if not self._connected:
            Logger.warning("WebSocket 连接超时，将继续运行（可能未连接 StreamDock）")

    @property
    def connected(self) -> bool:
        return self._connected

    def _on_open(self, ws, event: str, plugin_uuid: str):
        """连接建立后向 Stream Dock 注册插件"""
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
        """处理从 Stream Dock 接收到的 WebSocket 消息"""
        try:
            data = json.loads(message)
        except json.JSONDecodeError as e:
            Logger.error(f"JSON 解析失败: {e}")
            return

        try:
            self._handle_event(data)
        except Exception:
            Logger.error(f"处理事件 '{data.get('event')}' 异常:\n{traceback.format_exc()}")

    def _handle_event(self, data: Dict[str, Any]):
        event = data.get('event')
        Logger.info(f"收到事件: {event}")

        if event == 'didReceiveGlobalSettings':
            self.global_settings = data.get('payload', {}).get('settings')
            self._dispatch_global(Action.on_did_receive_global_settings, self.global_settings)
        elif event == 'willAppear':
            self._on_will_appear(data)
        elif event == 'willDisappear':
            self._on_will_disappear(data)
        elif event in CONTEXT_EVENTS:
            handler, extractor = CONTEXT_EVENTS[event]
            self._dispatch_context(data.get('context'), handler, extractor(data))
        elif event in GLOBAL_EVENTS:
            self._dispatch_global(GLOBAL_EVENTS[event], data)

    def _on_will_appear(self, data: Dict[str, Any]):
        context = data.get('context')
        if not context or context in self.actions:
            return
        action = ActionFactory.create_action(
            data.get('action', ''),
            context,
            data.get('payload', {}).get('settings', {}),
            self
        )
        if not action:
            Logger.error(f"创建 Action 失败: context={context}")
            return
        self.actions[context] = action
        action.on_will_appear()

    def _on_will_disappear(self, data: Dict[str, Any]):
        context = data.get('context')
        action = self.actions.pop(context, None) if context else None
        if action:
            action.on_will_disappear()

    def _dispatch_context(self, context: Optional[str], handler: Callback, payload: Any):
        """将事件转发给指定 context 的 Action"""
        action = self.actions.get(context) if context else None
        if action is None:
            return
        handler(action, payload)

    def _dispatch_global(self, handler: Callback, payload: Any):
        """将事件广播给所有 Action"""
        for action in list(self.actions.values()):
            handler(action, payload)

    def _send(self, event: str, **fields: Any):
        if not self.ws:
            return
        try:
            self.ws.send(json.dumps({'event': event, **fields}))
        except Exception as e:
            Logger.error(f"发送 {event} 失败: {e}")

    def set_global_settings(self, payload: Any):
        """更新插件的全局设置"""
        self._send('setGlobalSettings', context=self.plugin_uuid, payload=payload)
        self.global_settings = payload

    def get_global_settings(self):
        """请求获取插件的全局设置，结果通过 didReceiveGlobalSettings 返回"""
        self._send('getGlobalSettings', context=self.plugin_uuid)

    def get_action(self, context: str) -> Optional[Action]:
        """获取指定 context 的 Action 实例"""
        return self.actions.get(context)

    def get_actions(self, action: str) -> List[Action]:
        """获取所有指定类型的 Action 实例"""
        return [a for a in self.actions.values() if a.action == action]

    def stop(self):
        """关闭 WebSocket 连接"""
        if self.ws:
            self.ws.close()
        Logger.info("Plugin stopped")

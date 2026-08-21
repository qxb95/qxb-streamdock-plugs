import json
import threading
import websocket
import logging
import os
import sys
from typing import Any, Dict, List, Optional
from .timer import Timer
from .action import Action
from .logger import Logger

class Plugin:
    """Stream Dock插件的核心类，负责管理WebSocket连接和处理Stream Dock事件。
    
    该类维护与Stream Dock软件的WebSocket连接，处理各种事件（如按钮出现、消失、设置更改等），
    并管理插件的动作(Action)实例。每个动作实例对应Stream Dock界面上的一个按钮。
    """
    
    def __init__(self, port: int, plugin_uuid: str, event: str, info: Dict[str, Any]):
        """初始化插件实例
        
        Args:
            port: WebSocket服务器端口号
            plugin_uuid: 插件的唯一标识符
            event: 事件类型
            info: 包含插件信息的对象
        """
        self.actions: Dict[str, Action] = {}
        self.global_settings: Any = None
        self.timer = Timer()
        self.plugin_uuid = plugin_uuid

        # Initialize WebSocket
        self.ws = websocket.WebSocketApp(
            f'ws://127.0.0.1:{port}',
            on_open=lambda ws: self._on_open(ws, event, plugin_uuid),
            on_message=self._on_message,
            on_error=lambda ws, error: Logger.error(f"WebSocket error: {error}")
        )
        
        # Start WebSocket connection in a separate thread
        threading.Thread(target=self.ws.run_forever, daemon=True).start()
    
    def _on_open(self, ws, event: str, plugin_uuid: str):
        """WebSocket连接建立时的回调函数
        
        向Stream Dock注册插件，发送初始化事件。
        
        Args:
            ws: WebSocket连接实例
            event: 事件类型
            plugin_uuid: 插件UUID
        """        
        Logger.info("WebSocket connected")
        
        ws.send(json.dumps({'event': event, 'uuid': plugin_uuid}))
    
    def _on_message(self, ws, message):
        """处理从Stream Dock接收到的WebSocket消息
        
        根据接收到的事件类型执行相应的操作，包括：
        - 处理全局settings更新
        - 处理按钮出现/消失事件
        - 处理按钮settings更改
        - 处理标题参数更改
        
        Args:
            ws: WebSocket连接实例
            message: 接收到的JSON消息
        """        
        data = json.loads(message)
        event = data.get('event')
        Logger.info(event)
        if event == 'didReceiveGlobalSettings':
            self.global_settings = data.get('payload', {}).get('settings')
            for action in self.actions.values():
                if hasattr(action, 'on_did_receive_global_settings'):
                    action.on_did_receive_global_settings(self.global_settings)
        elif event == 'willAppear':
            context = data.get('context')
            if context not in self.actions:
                from .action_factory import ActionFactory
                action = ActionFactory.create_action(
                    data.get('action'),
                    context,
                    data.get('payload', {}).get('settings', {}),
                    self
                )
                if action:
                    self.actions[context] = action
                else:
                    Logger.error(f"Failed to create action for context: {context}")
        elif event == 'willDisappear':
            context = data.get('context')
            if context in self.actions:
                action = self.actions[context]
                if hasattr(action, 'on_will_disappear'):
                    action.on_will_disappear()
                del self.actions[context]
        elif event == 'didReceiveSettings':
            context = data.get('context')
            if context in self.actions:
                action = self.actions[context]
                settings = data.get('payload', {}).get('settings', {})
                if hasattr(action, 'on_did_receive_settings'):
                    action.on_did_receive_settings(settings)
                else:
                    action.settings = settings
        elif event == 'titleParametersDidChange':
            context = data.get('context')
            if context in self.actions:
                action = self.actions[context]
                payload = data.get('payload', {})
                if hasattr(action, 'on_title_parameters_did_change'):
                    action.on_title_parameters_did_change(payload)
                else:
                    action.title = payload.get('title', '')
                    action.title_parameters = payload.get('titleParameters', {})
        # Handle context-specific events
        context_events = {
            'keyDown': 'on_key_down',
            'keyUp': 'on_key_up',
            'dialDown': 'on_dial_down',
            'dialUp': 'on_dial_up',
            'dialRotate': 'on_dial_rotate'
        }
        
        if event in context_events:
            context = data.get('context')
            if context in self.actions:
                action = self.actions[context]
                handler = context_events[event]
                if hasattr(action, handler):
                    getattr(action, handler)(data.get('payload', {}))
        # Handle global events
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
        elif event == 'propertyInspectorDidAppear':
            context = data.get('context')
            if context in self.actions:
                action = self.actions[context]
                if hasattr(action, 'on_property_inspector_did_appear'):
                    action.on_property_inspector_did_appear(data)
        elif event == 'propertyInspectorDidDisappear':
            context = data.get('context')
            if context in self.actions:
                action = self.actions[context]
                if hasattr(action, 'on_property_inspector_did_disappear'):
                    action.on_property_inspector_did_disappear(data)
        elif event == 'sendToPlugin':
            context = data.get('context')
            if context in self.actions:
                action = self.actions[context]
                if hasattr(action, 'on_send_to_plugin'):
                    action.on_send_to_plugin(data.get('payload', {}))
    
    def set_global_settings(self, payload: Any):
        """更新插件的全局设置
        
        Args:
            payload: 新的全局设置值
        """        
        self.ws.send(json.dumps({
            'event': 'setGlobalSettings',
            'context': self.plugin_uuid,
            'payload': payload
        }))
        self.global_settings = payload
    
    def get_global_settings(self):
        """请求获取插件的当前全局设置
        
        发送请求后，设置值将通过WebSocket消息返回
        """        
        self.ws.send(json.dumps({
            'event': 'getGlobalSettings',
            'context': self.plugin_uuid
        }))
    
    def get_action(self, context: str) -> Optional[Action]:
        """获取指定上下文的Action实例
        
        Args:
            context: Action的上下文标识符
            
        Returns:
            如果存在则返回Action实例，否则返回None
        """        
        return self.actions.get(context)
    
    def get_actions(self, action: str) -> List[Action]:
        """获取所有指定类型的Action实例列表
        
        Args:
            action: Action的类型标识符
            
        Returns:
            符合指定类型的Action实例列表
        """        
        return [a for a in self.actions.values() if a.action == action]
    
    def stop(self):
        """停止插件服务

        关闭与 Stream Dock 的 WebSocket 连接
        """
        if self.ws:
            self.ws.close()
            Logger.info("WebSocket closed")

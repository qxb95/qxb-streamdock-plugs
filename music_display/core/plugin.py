import json
import threading
import websocket
import logging
import os
import sys
from typing import Any, Dict, List, Optional
from http.server import HTTPServer, BaseHTTPRequestHandler
from .timer import Timer
from .action import Action
from .logger import Logger
from .action_factory import ActionFactory
from websocket import WebSocketApp


class Plugin:
    def __init__(self, port: int, plugin_uuid: str, event: str, info: Dict[str, Any]):
        self.actions: Dict[str, Action] = {}
        self.global_settings: Any = None
        self.timer = Timer()
        self.plugin_uuid = plugin_uuid
        self.http_server = None
        self.http_server_thread = None

        self.ws = websocket.WebSocketApp(
            f'ws://127.0.0.1:{port}',
            on_open=lambda ws: self._on_open(ws, event, plugin_uuid),
            on_message=self._on_message,
            on_error=lambda ws, error: Logger.error(f"WebSocket error: {error}")
        )

        threading.Thread(target=self.ws.run_forever, daemon=True).start()

    def _on_open(self, ws, event: str, plugin_uuid: str):
        Logger.info("WebSocket connected")
        ws.send(json.dumps({'event': event, 'uuid': plugin_uuid}))

    def _on_message(self, ws, message):
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
        self.ws.send(json.dumps({
            'event': 'setGlobalSettings',
            'context': self.plugin_uuid,
            'payload': payload
        }))
        self.global_settings = payload

    def get_global_settings(self):
        self.ws.send(json.dumps({
            'event': 'getGlobalSettings',
            'context': self.plugin_uuid
        }))

    def get_action(self, context: str) -> Optional[Action]:
        return self.actions.get(context)

    def get_actions(self, action: str) -> List[Action]:
        return [a for a in self.actions.values() if a.action == action]

    def stop(self):
        if self.http_server:
            self.http_server.shutdown()
            self.http_server.server_close()
            Logger.info("HTTP server stopped")
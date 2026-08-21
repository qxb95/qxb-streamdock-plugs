"""插件入口的公共实现：解析 StreamDock 传入的命令行参数并运行插件。"""
import argparse
import sys
import threading
import time
import traceback
from typing import Optional

from .action_factory import ActionFactory
from .logger import Logger
from .plugin import Plugin

#: StreamDock 启动插件前的等待时间（秒），避免连接过早
STARTUP_DELAY = 1


def parse_args(name: str) -> argparse.Namespace:
    """解析 StreamDock 传给插件的命令行参数"""
    parser = argparse.ArgumentParser(description=f'Stream Dock Plugin ({name})')
    parser.add_argument('-port', type=int, required=True, help='WebSocket port number')
    parser.add_argument('-pluginUUID', type=str, required=True, help='Unique identifier for the plugin')
    parser.add_argument('-registerEvent', type=str, required=True, help='Event type for plugin registration')
    parser.add_argument('-info', type=str, required=True,
                        help='JSON string containing Stream Dock and device information')
    return parser.parse_args()


def run_plugin(name: str, actions_dir: Optional[str] = None) -> None:
    """插件主循环：注册 Action、建立连接，并在连接关闭时退出

    Args:
        name: 插件名称，仅用于日志
        actions_dir: actions 目录，缺省时自动查找 actions/ 或 src/actions/
    """
    Logger.info(f"{name} Plugin Start")
    args = parse_args(name)

    try:
        ActionFactory.scan_and_register_actions(actions_dir)
        time.sleep(STARTUP_DELAY)
        plugin = Plugin(args.port, args.pluginUUID, args.registerEvent, args.info)
        stop_event = threading.Event()
        plugin_on_close = plugin.ws.on_close

        def on_close(ws, close_status_code, close_msg):
            if plugin_on_close:
                plugin_on_close(ws, close_status_code, close_msg)
            plugin.stop()
            stop_event.set()

        plugin.ws.on_close = on_close
        stop_event.wait()
    except Exception:
        Logger.error(f"插件运行异常:\n{traceback.format_exc()}")
        sys.exit(1)

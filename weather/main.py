import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import argparse
import threading
import time
import traceback
from src.core.plugin import Plugin
from src.core.logger import Logger
from src.core.action_factory import ActionFactory
from src.actions.weather import Weather

ActionFactory.register_action('weather', Weather)
Logger.info("[Main] 手动注册 Action: weather")

def main():
    Logger.info("Weather Plugin Start")
    parser = argparse.ArgumentParser()
    parser.add_argument('-port', type=int, required=True)
    parser.add_argument('-pluginUUID', type=str, required=True)
    parser.add_argument('-registerEvent', type=str, required=True)
    parser.add_argument('-info', type=str, required=True)
    args = parser.parse_args()

    try:
        time.sleep(1)
        plugin = Plugin(args.port, args.pluginUUID, args.registerEvent, args.info)
        stop_event = threading.Event()
        def on_close(ws, close_status_code, close_msg):
            plugin.stop()
            stop_event.set()
            Logger.info('Plugin stopped')
        plugin.ws.on_close = on_close
        stop_event.wait()
    except Exception:
        Logger.error(f"插件运行异常:\n{traceback.format_exc()}")
        sys.exit(1)

if __name__ == '__main__':
    main()
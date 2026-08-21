import logging
import os
from typing import Optional

from .paths import log_dir

_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'


class Logger:
    """全局日志管理类

    使用单例模式实现的日志管理器，提供统一的日志记录接口。
    日志同时输出到控制台和插件目录下的 logs/plugin.log。
    """

    _instance: Optional['Logger'] = None
    _logger: Optional[logging.Logger] = None

    def __new__(cls) -> 'Logger':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._setup_logger()
        return cls._instance

    @classmethod
    def get_instance(cls) -> 'Logger':
        if cls._instance is None:
            cls._instance = Logger()
        return cls._instance

    @classmethod
    def _setup_logger(cls):
        if cls._logger is not None:
            return
        cls._logger = logging.getLogger('StreamDock')
        cls._logger.setLevel(logging.INFO)

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter(_FORMAT))
        cls._logger.addHandler(console_handler)

        try:
            base_path = log_dir()
            os.makedirs(base_path, exist_ok=True)
            file_handler = logging.FileHandler(os.path.join(base_path, 'plugin.log'), encoding='utf-8')
            file_handler.setFormatter(logging.Formatter(_FORMAT))
            cls._logger.addHandler(file_handler)
        except Exception as e:
            print(f"Failed to setup file handler: {e}")

    @classmethod
    def get_logger(cls) -> logging.Logger:
        if cls._logger is None:
            cls._setup_logger()
        return cls._logger

    @classmethod
    def info(cls, message):
        cls.get_instance().get_logger().info(message)

    @classmethod
    def error(cls, message):
        cls.get_instance().get_logger().error(message)

    @classmethod
    def warning(cls, message):
        cls.get_instance().get_logger().warning(message)

    @classmethod
    def debug(cls, message):
        cls.get_instance().get_logger().debug(message)

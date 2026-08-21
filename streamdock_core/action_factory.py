import importlib
import inspect
import os
import sys
import traceback
from typing import Dict, Optional, Type

from .action import Action
from .logger import Logger
from .paths import app_dir, bundle_dir

#: 自动扫描时依次尝试的 actions 目录（相对插件目录）
ACTIONS_DIR_CANDIDATES = (
    ('actions',),
    ('src', 'actions'),
)


class ActionFactory:
    """Action 工厂类，负责注册 action 类型并按 UUID 创建实例"""

    _action_types: Dict[str, Type[Action]] = {}

    @classmethod
    def register_action(cls, action_type: str, action_class: Type[Action]):
        """注册一个 Action 类型

        Args:
            action_type: Action 的类型标识符，即 UUID 的最后一段
            action_class: Action 的具体实现类
        """
        cls._action_types[action_type] = action_class

    @classmethod
    def create_action(cls, action: str, context: str, settings: dict, plugin) -> Optional[Action]:
        """创建一个 Action 实例

        Args:
            action: Action 的标识符，可以是完整的 action 字符串（如 com.xxx.xxx.time）
            context: Action 的上下文标识符
            settings: Action 的设置
            plugin: 所属的 Plugin 实例

        Returns:
            对应类型已注册时返回 Action 实例，否则返回 None
        """
        try:
            action_name = (action or '').split('.')[-1]
            action_class = cls._action_types.get(action_name)
            if not action_class:
                Logger.error(f"Action type not found: {action_name}")
                return None
            action_instance = action_class(action, context, settings, plugin)
            if not isinstance(action_instance, Action):
                Logger.error(f"Created instance is not an Action type: {action_name}")
                return None
            return action_instance
        except Exception as e:
            Logger.error(f"Error creating action {action}: {str(e)}")
            Logger.error(traceback.format_exc())
            return None

    @classmethod
    def find_actions_dir(cls) -> Optional[str]:
        """查找插件的 actions 目录，兼容 actions/ 与 src/actions/ 两种布局"""
        for base_path in (bundle_dir(), app_dir()):
            for relative in ACTIONS_DIR_CANDIDATES:
                candidate = os.path.join(base_path, *relative)
                if os.path.isdir(candidate):
                    return candidate
        return None

    @classmethod
    def scan_and_register_actions(cls, actions_dir: Optional[str] = None):
        """扫描 actions 目录并注册其中所有的 Action 子类

        每个模块中的 Action 子类都以模块名（小写）作为类型标识符注册。

        Args:
            actions_dir: actions 目录，缺省时自动查找
        """
        actions_dir = actions_dir or cls.find_actions_dir()
        if not actions_dir:
            Logger.error("Actions directory not found")
            return

        parent_dir = os.path.dirname(actions_dir)
        if parent_dir not in sys.path:
            sys.path.insert(0, parent_dir)

        for file_name in sorted(os.listdir(actions_dir)):
            if not file_name.endswith('.py') or file_name.startswith('__'):
                continue
            module_name = file_name[:-3]
            try:
                module = importlib.import_module(f'actions.{module_name}')
                Logger.info(f"Loading action module: {module_name}")
                for _, obj in inspect.getmembers(module):
                    if inspect.isclass(obj) and issubclass(obj, Action) and obj is not Action:
                        action_type = module_name.lower()
                        cls.register_action(action_type, obj)
                        Logger.info(f"Successfully registered action: {action_type} -> {obj.__name__}")
            except Exception as e:
                Logger.error(f"Error loading action module {module_name}: {str(e)}")
                Logger.error(traceback.format_exc())

# src/core/action_factory.py
import os
import importlib
import inspect
from typing import Dict, Type, Optional
from .action import Action
from .logger import Logger


class ActionFactory:
    _action_types: Dict[str, Type[Action]] = {}

    @classmethod
    def register_action(cls, action_type: str, action_class: Type[Action]):
        cls._action_types[action_type] = action_class

    @classmethod
    def create_action(cls, action: str, context: str, settings: dict, plugin) -> Optional[Action]:
        try:
            action_name = action.split('.')[-1]
            action_class = cls._action_types.get(action_name)
            if action_class:
                action_instance = action_class(action, context, settings, plugin)
                if not isinstance(action_instance, Action):
                    Logger.error(f"Created instance is not an Action type: {action_name}")
                    return None
                return action_instance
            else:
                Logger.error(f"Action type not found: {action_name}")
            return None
        except Exception as e:
            Logger.error(f"Error creating action {action}: {str(e)}")
            return None

    @classmethod
    def scan_and_register_actions(cls):
        import sys

        if getattr(sys, 'frozen', False):
            base_path = sys._MEIPASS
            actions_dir = os.path.join(base_path, 'src', 'actions')
        else:
            actions_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'actions')

        if not os.path.exists(actions_dir):
            Logger.error(f"Actions directory not found: {actions_dir}")
            return

        src_dir = os.path.dirname(actions_dir)
        if src_dir not in sys.path:
            sys.path.insert(0, src_dir)

        for file_name in os.listdir(actions_dir):
            if file_name.endswith('.py') and not file_name.startswith('__'):
                module_name = file_name[:-3]
                try:
                    module = importlib.import_module(f'actions.{module_name}')
                    Logger.info(f"Loading action module: {module_name}")
                    for name, obj in inspect.getmembers(module):
                        if (inspect.isclass(obj) and
                                issubclass(obj, Action) and
                                obj != Action):
                            action_type = module_name.lower()
                            cls.register_action(action_type, obj)
                            Logger.info(f"Successfully registered action: {action_type} -> {obj.__name__}")
                except Exception as e:
                    Logger.error(f"Error loading action module {module_name}: {str(e)}")
                    import traceback
                    Logger.error(traceback.format_exc())


# 自动扫描
ActionFactory.scan_and_register_actions()
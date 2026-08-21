"""运行环境路径工具：统一处理开发环境与 PyInstaller 打包后的路径差异。"""
import os
import sys


def is_frozen() -> bool:
    """是否运行在 PyInstaller 打包后的 exe 中"""
    return getattr(sys, 'frozen', False)


def app_dir() -> str:
    """插件所在目录（打包后为 exe 所在目录，开发环境为入口脚本所在目录）"""
    if is_frozen():
        return os.path.dirname(os.path.abspath(sys.executable))
    main_module = sys.modules.get('__main__')
    main_file = getattr(main_module, '__file__', None)
    if main_file:
        return os.path.dirname(os.path.abspath(main_file))
    return os.getcwd()


def bundle_dir() -> str:
    """打包资源所在目录（打包后为 sys._MEIPASS，开发环境同 app_dir）"""
    if is_frozen():
        return getattr(sys, '_MEIPASS', app_dir())
    return app_dir()


def find_resource(*relative_paths: str) -> str:
    """在 exe 外部目录和打包内部目录中依次查找资源

    Args:
        *relative_paths: 相对路径，如 'resources' 或 ('resources', 'bg.png')

    Returns:
        第一个存在的路径；都不存在时返回打包内部目录下的候选路径
    """
    candidates = [
        os.path.join(app_dir(), *relative_paths),
        os.path.join(bundle_dir(), *relative_paths),
    ]
    for candidate in candidates:
        if os.path.exists(candidate):
            return candidate
    return candidates[-1]


def log_dir() -> str:
    """日志目录（插件目录下的 logs）"""
    return os.path.join(app_dir(), 'logs')

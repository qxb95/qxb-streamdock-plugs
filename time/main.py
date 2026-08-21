# main.py
import os
import sys

# 插件目录用于导入 src 包，仓库根目录用于导入公共框架 streamdock_core
_PLUGIN_DIR = os.path.dirname(os.path.abspath(__file__))
for _path in (_PLUGIN_DIR, os.path.dirname(_PLUGIN_DIR)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from streamdock_core import run_plugin  # noqa: E402

if __name__ == '__main__':
    run_plugin('时钟')

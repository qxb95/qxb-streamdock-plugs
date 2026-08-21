#!/usr/bin/env bash
# 依次运行三个插件的单元测试并输出覆盖率。
# 三个插件各自拥有同名的顶层包（src / core），因此必须分别在独立的 pytest 进程中运行。
set -u
cd "$(dirname "$0")"

PYTHON="${PYTHON:-python3}"
STATUS=0

for plugin in time weather music_display; do
    echo ""
    echo "=============================================="
    echo " 运行 ${plugin} 插件测试"
    echo "=============================================="
    (cd "$plugin" && "$PYTHON" -m pytest "$@") || STATUS=1
done

exit "$STATUS"

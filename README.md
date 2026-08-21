此项目采用deepseek AI 编程
相关插件信息如下：
  1、基于高德API天气插件
  2、按钮表盘
  3、歌曲显示

## 单元测试

安装测试依赖后运行全部插件的测试与覆盖率统计：

```bash
pip install -r requirements-dev.txt
./run_tests.sh
```

三个插件各自拥有同名的顶层包（`src` / `core`），因此必须在独立的 pytest 进程中运行，
`run_tests.sh` 会依次进入每个插件目录执行 `pytest`。也可以单独运行某个插件：

```bash
cd weather && python -m pytest
```

测试使用替身模块模拟 WebSocket、定时器、高德天气接口以及仅存在于 Windows 的
`pycaw` / `winrt`，因此在任意平台均可运行。

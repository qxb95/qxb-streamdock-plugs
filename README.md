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

共享包 `streamdock_core` 的测试位于仓库根目录 `tests/`；三个插件各自拥有同名的顶层包
（`src` / `core`），因此必须在独立的 pytest 进程中运行，`run_tests.sh` 会先跑根目录测试，
再依次进入每个插件目录执行 `pytest`。也可以单独运行某个部分：

```bash
python -m pytest          # streamdock_core
cd weather && python -m pytest
```

测试使用替身模块模拟 WebSocket、定时器、高德天气接口以及仅存在于 Windows 的
`pycaw` / `winrt`，因此在任意平台均可运行。

## 公共代码 streamdock_core

三个插件共用仓库根目录下的 `streamdock_core` 包，不再各自维护一份框架代码：

- `Plugin`：WebSocket 连接、注册与事件分发
- `Action`：按键基类，含事件回调默认实现与 `set_title` / `set_image` 等指令
- `ActionFactory`：动态扫描 `actions/` 或 `src/actions/` 并注册 Action
- `Logger` / `Timer`：日志与毫秒级定时器
- `run_plugin(name)`：命令行参数解析与插件启动流程（各插件 `main.py` 仅调用它）
- `images`：`to_data_url` / `load_font` / `text_width`
- `paths`：`app_dir` / `bundle_dir` / `find_resource`，统一处理开发环境与 PyInstaller 打包路径

插件 `main.py` 会把仓库根目录加入 `sys.path`，打包时通过 `main.spec` 的 `pathex` 与 `hiddenimports` 引入该包。

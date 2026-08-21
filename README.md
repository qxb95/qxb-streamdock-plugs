此项目采用deepseek AI 编程
相关插件信息如下：
  1、基于高德API天气插件
  2、按钮表盘
  3、歌曲显示

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

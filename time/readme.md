# StreamDock 时钟插件项目说明文档

## 📋 项目概述

### 项目名称
StreamDock 时钟插件 (Clock Plugin)

### 项目描述
这是一个为 StreamDock 设备开发的 Python 插件，在设备按键上显示一个**模拟指针表盘时钟**，带有时针、分针、秒针，每秒自动刷新。支持自定义背景图片（500×500画布，400×400表盘居中）。

### 技术栈
| 技术 | 用途 |
|------|------|
| **Python 3.10+** | 开发语言 |
| **WebSocket** | 与 StreamDock 主程序通信 |
| **Pillow (PIL)** | 表盘图像渲染 |
| **PyInstaller** | 打包为独立可执行文件 |
| **websocket-client** | WebSocket 客户端 |

### 版本信息
- 当前版本：v1.0.0
- 作者：qxb
- UUID：`com.qxb.clock.time`

---

## 📁 项目目录结构

```
com.qxb.clock.sdPlugin/
├── main.py                        # 插件入口文件
├── manifest.json                  # 插件清单（UUID、Action 定义）
├── build_plugin.bat               # 一键打包脚本（Windows）
├── main.spec                      # PyInstaller 打包配置
├── background.png                 # 可选：自定义背景图片（500×500）
├── src/
│   ├── __init__.py
│   ├── core/                      # 核心框架
│   │   ├── __init__.py
│   │   ├── action.py              # Action 基类
│   │   ├── plugin.py              # Plugin 核心类（WebSocket 管理）
│   │   ├── logger.py              # 日志系统
│   │   ├── timer.py               # 定时器（毫秒精度）
│   │   ├── action_factory.py      # Action 工厂（自动扫描注册）
│   │   └── renderer.py            # 表盘渲染（独立模块，支持背景图）
│   └── actions/                   # Action 实现
│       ├── __init__.py
│       └── time.py                # 时钟 Action
└── logs/                          # 运行时日志（自动生成）
    └── plugin.log                 # 插件运行日志
```

---

## 🔧 核心模块说明

### 1️⃣ `main.py` — 入口文件

**功能**：
- 解析 StreamDock 主程序传递的命令行参数（`-port`、`-pluginUUID`、`-registerEvent`、`-info`）
- 创建 `Plugin` 实例并保持运行
- 无参数时进入调试模式，生成 10 张表盘图片到 `debug_output/`

**关键代码**：
```python
# 使用 -registerEvent（注意不是 -event）
parser.add_argument('-registerEvent', type=str, required=True)
plugin = Plugin(args.port, args.pluginUUID, args.registerEvent, args.info)
stop_event.wait()  # 阻塞等待，直到 WebSocket 关闭
```

---

### 2️⃣ `src/core/plugin.py` — WebSocket 核心

**功能**：
- 建立与 StreamDock 主程序的 WebSocket 连接
- 分发事件（`willAppear`、`willDisappear`、`keyDown`、`keyUp` 等）
- 管理所有 Action 实例

**关键特性**：
- 连接超时不会抛异常，仅记录警告（确保进程不崩溃）
- 支持 WebSocket 自动重连
- 通过 `ActionFactory` 动态创建 Action 实例

---

### 3️⃣ `src/core/timer.py` — 定时器

**API**：
```python
timer.set_interval(uuid: str, delay_ms: int, callback: Callable)
timer.clear_interval(uuid: str)
```
- `delay_ms`：毫秒单位（例如 1000 = 1 秒）
- 内部使用守护线程，不影响主循环

---

### 4️⃣ `src/core/action_factory.py` — Action 工厂

**功能**：
- 自动扫描 `src/actions/` 目录
- 根据 `manifest.json` 中 UUID 的最后一段（如 `time`）查找对应的 Python 类
- 类名必须与文件名一致（如 `time.py` → `class Time`）

**注册逻辑**：
```python
action_name = action.split('.')[-1]  # com.qxb.clock.time → time
action_class = cls._action_types.get(action_name)
```

---

### 5️⃣ `src/core/renderer.py` — 表盘渲染

**功能**：
- 独立表盘渲染函数 `render_clock(canvas_size=500, dial_size=400)`
- 支持自定义背景图片（自动缩放到 `canvas_size`）
- 背景缓存，提高性能

**背景图片加载顺序**：
1. 项目根目录 `background.png`
2. 插件目录 `background.png`
3. `debug_output/background.png`

**渲染内容**：
- 径向渐变背景（无背景图时）
- 外圈发光环
- 60 个刻度（主刻度带光晕）
- 时针、分针、秒针
- 中心装饰（带高光）

---

### 6️⃣ `src/actions/time.py` — 时钟 Action

**功能**：
- 按键出现时立即发送测试图片
- 每秒刷新一次表盘
- 按键点击时手动刷新

**生命周期**：
```python
willAppear → __init__() → 发送图片 → 启动定时器
willDisappear → 清除定时器
```

---

## 📦 打包与部署

### 打包工具
使用 `build_plugin.bat` 一键打包：

```batch
@echo off
pyinstaller main.spec --clean --noconfirm
# 自动生成 com.qxb.clock.sdPlugin 文件夹
```

### 打包配置 (`main.spec`)

```python
datas = [
    ('src', 'src'),               # 必须包含 src 目录
    ('manifest.json', '.'),
]

hiddenimports = [
    'src.core',
    'src.core.action',
    'src.core.plugin',
    'src.core.logger',
    'src.core.timer',
    'src.core.action_factory',
    'src.core.renderer',
    'src.actions.time',
    'PIL',
    'PIL.Image',
    'PIL.ImageDraw',
    'PIL.ImageFont',
    'websocket',
]
```

### 部署步骤

1. **运行打包**：`build_plugin.bat`
2. **复制插件文件夹**：
   ```
   复制 dist/com.qxb.clock.sdPlugin 到：
   %APPDATA%\HotSpot\StreamDock\plugins\
   ```
3. **重启 StreamDock** 主程序
4. **在 StreamDock 主界面**，将“时钟”动作拖拽到任意按键上

---

## 🐛 调试与日志

### 日志位置
```
插件目录/logs/plugin.log
```

### 关键日志

| 日志内容 | 含义 |
|----------|------|
| `StreamDock 插件启动` | 插件进程启动成功 |
| `WebSocket connected` | WebSocket 连接建立 |
| `Loading action module: time` | Action 文件被扫描 |
| `Successfully registered action: time -> Time` | Action 注册成功 |
| `[Time] 已初始化` | Action 实例创建成功 |
| `[Time] ✅ 测试图片已立即发送` | 图片发送成功 |

### 无设备调试
```bash
python main.py
```
生成 10 张图片到 `debug_output/`，用于验证表盘样式。

---

## 📝 API 参考

### Action 基类方法

| 方法 | 说明 |
|------|------|
| `set_image(url)` | 设置按键图片（Base64 data URI） |
| `set_title(title)` | 设置按键标题 |
| `set_state(state)` | 切换按键状态（0/1） |
| `set_settings(payload)` | 保存设置 |
| `open_url(url)` | 打开浏览器 |
| `show_ok()` / `show_alert()` | 显示成功/警告提示 |

### Plugin 方法

| 方法 | 说明 |
|------|------|
| `timer.set_interval(uuid, ms, callback)` | 设置定时器（毫秒） |
| `timer.clear_interval(uuid)` | 清除定时器 |
| `set_global_settings(payload)` | 设置全局配置 |

---

## 🔄 事件回调

| 回调 | 触发时机 |
|------|----------|
| `on_will_appear()` | 按键出现在屏幕上 |
| `on_will_disappear()` | 按键从屏幕消失 |
| `on_key_down(payload)` | 按键按下 |
| `on_key_up(payload)` | 按键释放 |
| `on_did_receive_settings(settings)` | 收到设置更新 |

---

## ❓ 常见问题排查

| 现象 | 原因 | 解决方案 |
|------|------|----------|
| 插件反复重启 | 插件进程提前退出 | 使用 `stop_event.wait()` 主循环，移除 `raise RuntimeError` |
| 无 `[Time] 已初始化` | `willAppear` 未触发 | 确认动作已拖拽到按键，`UUID` 与 `time.py` 匹配 |
| 手动测试无输出 | 缺少 `src` 文件夹 | 确保 `main.spec` 包含 `('src', 'src')` |
| 表盘不显示图片 | `set_image` 通信失败 | 检查 WebSocket 连接，查看日志错误 |
| 打包后找不到模块 | `hiddenimports` 缺失 | 添加 `src.actions.time` 等模块 |

---

## 📌 依赖版本

```txt
websocket-client==1.6.1
Pillow>=10.0.0
pyinstaller>=6.0.0
```

安装命令：
```bash
pip install -r requirements.txt
```

---

## 📞 联系方式

- **作者**：qxb
- **插件 UUID**：`com.qxb.clock`
- **Action UUID**：`com.qxb.clock.time`
- **问题反馈**：GitHub Issues 或官方社区

---

## ✅ 项目状态

| 功能 | 状态 |
|------|------|
| 表盘渲染 | ✅ 完成 |
| 背景图支持 | ✅ 完成 |
| 定时刷新 | ✅ 完成 |
| 无设备调试 | ✅ 完成 |
| 打包部署 | ✅ 完成 |
| 日志系统 | ✅ 完成 |
| 手动刷新 | ✅ 完成 |

---

*文档版本：v1.0.0*  
*最后更新：2026-08-19*
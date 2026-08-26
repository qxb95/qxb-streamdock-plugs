# StreamDock NAS 监控插件

## 📌 项目简介

本项目是一个为 **StreamDock** 设备开发的系统监控插件，基于 **Beszel Hub API** 获取 NAS/服务器的实时性能数据，并在 StreamDock 按键上以科技感十足的“悬浮球”动画直观展示。插件支持多指标切换（CPU、内存、磁盘、Swap、GPU），每个按钮可独立配置不同的 Beszel Hub 和 Agent，实现多设备集中监控。

所有配置通过属性检查器管理，持久化存储于 StreamDock 本地数据库，并支持自定义背景图片和球体大小。

---

## ✨ 主要功能

- 📊 **实时性能监控**：通过 Beszel Hub API 获取 CPU、内存、磁盘、Swap、GPU 使用率
- 🎯 **多设备支持**：每个按钮独立配置，可监控不同 Agent 或不同 Beszel Hub
- 🎨 **科技悬浮球显示**：径向渐变、玻璃高光、外发光效果，颜色随负载动态变化（绿→黄→红）
- 🖼️ **自定义背景**：支持透明背景或自定义图片（PNG/JPG）
- 🔄 **定时自动刷新**：可调刷新间隔（5-60 秒），点击按钮手动立即刷新
- 📐 **球体大小调节**：滑块控制悬浮球缩放比例（0.4-1.5 倍）
- 🔌 **独立 WebSocket 通信**：属性检查器独立连接，不依赖 Action 实例，配置稳定可靠
- 💾 **配置持久化**：所有设置由 StreamDock 软件统一管理，支持多按钮独立存储

---

## 🧱 技术架构

| 组件 | 技术/工具 |
| :--- | :--- |
| **开发语言** | Python 3.8+ |
| **UI 界面** | HTML + CSS + JavaScript（属性检查器） |
| **通信协议** | WebSocket（StreamDock SDK 标准） |
| **图片处理** | Pillow（PIL）— 径向渐变、高斯模糊、图像合成 |
| **HTTP 客户端** | Requests |
| **打包工具** | PyInstaller |
| **配置存储** | StreamDock 本地数据库（`settings.json`） |

---

## 📁 项目文件结构

```
com.yourcompany.streamdock.nasmonitor.sdPlugin/
├── manifest.json                 # 插件清单（定义 UUID、CodePath、PropertyInspectorPath）
├── main.py                       # 插件入口
├── main.spec                     # PyInstaller 打包配置
├── build.bat                     # Windows 一键打包脚本
├── requirements.txt              # Python 依赖列表
├── Property_Inspector/           # 属性检查器（配置界面）
│   └── nas_monitor.html          # 设置界面（含表单、状态反馈、WebSocket 通信）
├── backgrounds/                  # 背景图片目录（用户可自行添加）
│   └── tech.png                  # 示例背景图
└── src/                          # 源代码
    ├── core/                     # SDK 核心库
    │   ├── __init__.py
    │   ├── action.py             # Action 基类
    │   ├── plugin.py             # Plugin 主类
    │   ├── logger.py             # 日志管理
    │   ├── timer.py              # 定时器
    │   └── action_factory.py     # Action 工厂（自动扫描注册）
    └── actions/
        └── nasmonitor.py         # NAS 监控核心逻辑（Action 实现）
```

---

## ⚙️ 配置说明

### 属性检查器配置项

| 字段 | 类型 | 说明 |
| :--- | :--- | :--- |
| `beszel_url` | string | Beszel Hub 地址（含协议和端口，如 `http://192.168.1.100:8090`） |
| `beszel_email` | string | Beszel 登录邮箱 |
| `beszel_password` | string | Beszel 登录密码 |
| `beszel_agent` | string | 要监控的 Agent 名称（须与 Beszel 中一致） |
| `refresh_interval` | integer | 刷新间隔（秒），最小值 5 |
| `metric` | string | 显示指标：`cpu` / `mp`（内存）/ `dp`（磁盘）/ `s`（Swap）/ `gpu_pct` |
| `ball_scale` | float | 球体缩放比例（0.4-1.5），默认 0.9 |
| `bg_image` | string | 背景图片相对路径（如 `backgrounds/tech.png`） |

### 配置存储位置

所有配置由 StreamDock 软件统一管理，存储于：
- Windows: `%APPDATA%\HotSpot\StreamDock\plugins\{UUID}.sdPlugin\settings.json`
- macOS: `~/Library/Application Support/HotSpot/StreamDock/plugins/{UUID}.sdPlugin/settings.json`

每个按钮（context）独立存储，互不干扰。

---

## 🚀 快速开始

### 1. 环境准备

```bash
# 安装 Python 依赖
pip install -r requirements.txt
```

### 2. 配置 Beszel

确保 Beszel Hub 已部署并添加了需要监控的 Agent。

### 3. 打包插件

```bash
# Windows 双击运行 build.bat
# 或手动执行
pyinstaller main.spec --clean --noconfirm
```

### 4. 安装到 StreamDock

- 自动安装：打包完成后按提示输入 `y`
- 手动安装：将 `dist/{UUID}.sdPlugin` 复制到 StreamDock 插件目录

### 5. 使用

1. 重启 StreamDock
2. 从插件列表拖拽 **"NAS 监控"** 到设备按键
3. 右键 → 属性，填写 Beszel 连接信息
4. 保存配置，开始监控

---

## 🔧 开发与调试

### 测试模式（无硬件）

```bash
python generate_nas_image.py -o test.png
```

生成悬浮球预览图，支持模拟数据和真实 Beszel 数据：

```bash
# 模拟数据
python generate_nas_image.py --metric cpu -o test.png

# 真实数据
python generate_nas_image.py --real --url http://hub:8090 --email admin@xxx --password pass --agent nas1 --metric mp -o real.png

# 带背景和自定义尺寸
python generate_nas_image.py --bg backgrounds/tech.png --ball-scale 0.8 -s 120,120 -o custom.png
```

### 查看日志

日志文件位置：插件目录下的 `logs/plugin.log`

```bash
# 开发环境
tail -f logs/plugin.log

# Windows 打包后
type "%APPDATA%\HotSpot\StreamDock\plugins\{UUID}.sdPlugin\logs\plugin.log"
```

### 调试属性检查器

- 在 StreamDock 中右键按钮 → 属性
- 按 `F12` 打开开发者工具
- 查看 Console 日志和 WebSocket 消息

---

## 🧩 核心数据流

```
┌──────────────────────────────────────────────────────────────────────────┐
│                         1. 用户打开属性面板                               │
│   Property Inspector → WebSocket → StreamDock → Plugin → Action         │
│   Action.on_property_inspector_did_appear → send_to_property_inspector  │
└──────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                         2. 用户保存配置                                   │
│   Property Inspector → WebSocket({ event: 'setSettings', payload })     │
│   → Plugin._on_message('didReceiveSettings') → Action 更新配置           │
└──────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                         3. 定时/手动刷新                                  │
│   Timer → Action._refresh_data() → BeszelClient.get_latest_stats()     │
│   → generate_float_ball() → Base64 → set_image()                       │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 🛠️ 常见问题

### Q: 按钮显示 "❌ 未配置"

- 原因：尚未保存配置或配置信息不完整
- 解决：打开属性面板，填写完整的 Beszel 信息并保存

### Q: 按钮显示 "⚠️ 错误"

- 原因：连接 Beszel Hub 失败或 Agent 不存在
- 解决：
  1. 检查 `logs/plugin.log` 查看详细错误
  2. 确认 Beszel Hub 地址可访问
  3. 验证 Agent 名称是否正确

### Q: 属性面板提示 "无法与插件通讯"

- 原因：Property Inspector HTML 路径错误或 WebSocket 未连接
- 解决：
  1. 检查 `manifest.json` 中 `PropertyInspectorPath` 是否为 `Property_Inspector/nas_monitor.html`
  2. 确认 `Property_Inspector` 目录在插件根目录
  3. 重启 StreamDock 软件

### Q: Action type not found: xxx

- 原因：文件名与 UUID 最后一段不匹配
- 解决：将 `src/actions/` 中的文件名改为与 UUID 最后一段一致（如 `nasmonitor.py`）

### Q: 设置保存后不生效

- 原因：Action 未成功创建或配置未同步
- 解决：
  1. 查看日志确认 `Successfully registered action: xxx`
  2. 重启插件后重试
  3. 检查 `settings.json` 是否更新

### Q: 背景图片不显示

- 原因：路径错误或图片格式不支持
- 解决：
  1. 确认图片路径相对于插件根目录
  2. 支持格式 PNG/JPG
  3. 使用绝对路径测试

### Q: 颜色变化不流畅

- 原因：数值跳动或刷新间隔过长
- 解决：
  1. 缩短刷新间隔（如 5 秒）
  2. 检查数据源是否稳定

---

## 📜 许可证

本项目基于 **MIT 许可证** 开源，可自由使用、修改和分发。

> MIT 许可证要求派生作品必须保留原始的版权声明和许可声明，本项目采用 MIT 许可证以最大程度地促进协作和代码复用。

---

## 🙏 致谢

- [StreamDock 官方 SDK](https://github.com/MiraboxSpace/StreamDock-Device-SDK)
- [Beszel](https://beszel.dev/) — 轻量级服务器监控平台
- [Pillow](https://python-pillow.org/) — Python 图像处理库

---

**Happy monitoring!** 📊
# 高德天气插件 for StreamDock

## 📌 项目简介

本项目是一个为 **StreamDock** 设备开发的天气插件，基于 **高德地图 Web 服务 API** 获取实时天气数据，并在 StreamDock 按键上以自定义背景、自定义字体颜色和描边的方式清晰显示。插件支持完整的配置管理，所有设置持久化存储于 `config.json` 文件中，并同步到 StreamDock 内部存储，确保前端属性检查器能够稳定读取和显示配置。

---

## ✨ 主要功能

- 🌤 **实时天气获取**：通过高德 API 获取指定城市的实时天气（温度、天气状况）。
- 🎨 **自定义背景**：支持预设背景图片（PNG）或纯色背景。
- 📝 **灵活显示**：可选择是否显示城市名、温度、天气描述。
- 🔠 **字体大小调节**：支持小（8px）、中（10px）、大（12px）。
- 🎨 **字体颜色自定义**：支持任意颜色，文字清晰可读。
- 🖌️ **描边颜色自定义**：可设置文字描边颜色，提升可读性；若与字体颜色相同则自动消除描边，避免加粗。
- 🔑 **API Key 管理**：支持属性检查器配置，也可通过 `config.json` 文件持久化存储。
- 🧪 **Key 测试**：在属性检查器中可一键测试 API Key 是否有效。
- 💾 **配置持久化**：所有配置保存于 `config.json`（与插件 exe 同级），支持热加载（修改后无需重启插件）。
- ⏰ **定时刷新**：每隔 30 分钟自动刷新天气，也可手动点击按键刷新。

---

## 🧱 技术架构

| 组件 | 技术/工具 |
| :--- | :--- |
| **开发语言** | Python 3.9+ |
| **UI 界面** | HTML + CSS + JavaScript（属性检查器） |
| **通信协议** | WebSocket（StreamDock SDK 标准） |
| **图片处理** | Pillow（PIL） |
| **图标字体** | iconfont（自定义天气图标） |
| **打包工具** | PyInstaller |
| **配置存储** | JSON 文件 (`config.json`) + StreamDock 内部存储（双写） |

---

## 📁 项目文件结构

```
com.qxb.weather.sdPlugin/
├── manifest.json                 # 插件清单（定义 UUID、动作、CodePath 等）
├── main.py                       # 插件入口（启动 WebSocket 服务）
├── main.spec                     # PyInstaller 打包配置文件
├── build.bat                     # Windows 一键打包脚本
├── requirements.txt              # Python 依赖列表
├── config.json                   # 用户配置文件（自动生成/手动创建）
├── resources/                    # 资源文件夹
│   ├── bg_default.png            # 默认背景图片（72x72）
│   ├── bg_dark.png               # 深色背景图片（可选）
│   ├── bg_light.png              # 浅色背景图片（可选）
│   └── iconfont.ttf              # 天气图标字体文件
├── property_inspector/           # 属性检查器（设置界面）
│   └── index.html                # 设置界面 HTML（含颜色选择器）
└── src/                          # 源代码
    ├── core/                     # SDK 核心库（从模板复制，无需修改）
    │   ├── action.py
    │   ├── plugin.py
    │   ├── logger.py
    │   ├── timer.py
    │   └── action_factory.py
    └── actions/
        ├── __init__.py
        └── weather.py            # 天气插件核心逻辑（Action 实现）
```

---

## ⚙️ 配置说明

### 1. `config.json` 示例

```json
{
    "apiKey": "您的高德Web服务Key",
    "city": "北京",
    "showCity": true,
    "showTemp": true,
    "showWeatherDesc": true,
    "fontSize": 10,
    "textColor": "#ffffff",
    "strokeColor": "#000000",
    "bgType": "image",
    "bgImage": "bg_default.png",
    "bgColor": "#2c3e50"
}
```

### 2. 配置项详细说明

| 字段 | 类型 | 说明 |
| :--- | :--- | :--- |
| `apiKey` | string | 高德 Web 服务 Key（必填，否则无法获取天气） |
| `city` | string | 城市名称（如“北京”“上海”） |
| `showCity` | boolean | 是否显示城市名 |
| `showTemp` | boolean | 是否显示温度 |
| `showWeatherDesc` | boolean | 是否显示天气描述 |
| `fontSize` | integer | 文字大小（8/10/12） |
| `textColor` | string | 字体颜色（十六进制，如 `#ffffff`） |
| `strokeColor` | string | 描边颜色（十六进制，如 `#000000`；若与 `textColor` 相同则无描边） |
| `bgType` | string | 背景类型（`"image"` 或 `"color"`） |
| `bgImage` | string | 背景图片文件名（位于 `resources/` 下） |
| `bgColor` | string | 自定义颜色（十六进制，如 `#2c3e50`） |

### 3. 属性检查器（前端设置界面）

通过 StreamDock 右键按键 → **属性检查器** 可打开设置界面，支持：

- 输入/修改 API Key（以隐藏字符显示）
- 选择城市
- 勾选显示内容
- 调整字体大小
- 选择字体颜色和描边颜色
- 选择背景图片或自定义颜色
- 测试 API Key 有效性

> 💡 **提示**：属性检查器中的修改会保存到 `config.json`，同时通过 `setSettings` 同步到 StreamDock 内部存储，确保前后端数据一致。

---

## 🔧 开发与调试

### 1. 环境准备

- Python 3.9+
- 安装依赖：`pip install -r requirements.txt`
- 获取高德 API Key：登录 [高德开放平台](https://lbs.amap.com/) 创建 Web 服务 Key。

### 2. 测试模式（无硬件）

```bash
python main.py
```

会生成 `test_weather.png`，预览天气按钮效果。

### 3. 打包发布

- 运行 `build.bat`（Windows）生成 `dist` 目录。
- 将 `dist` 重命名为 `com.qxb.weather.sdPlugin`。
- 复制到 StreamDock 插件目录（如 `%APPDATA%\HotSpot\StreamDock\plugins\`）。
- 重启 StreamDock 即可使用。

### 4. 查看日志

插件运行日志位于插件目录下的 `logs/plugin.log`，可帮助排查问题。

---

## 🧩 核心数据流

1. **启动时**：后端读取 `config.json` → 应用配置 → 通过 `set_settings` 同步到 StreamDock 存储。
2. **属性检查器打开**：前端发送 `getSettings` → StreamDock 返回 `didReceiveSettings`（含配置）→ 前端回填表单。
3. **用户保存**：前端发送 `setSettings` → 后端 `on_did_receive_settings` 触发 → 保存到 `config.json` → 刷新天气。
4. **定时/手动刷新**：后端重新读取 `config.json` → 应用新配置 → 同步到 StreamDock 存储 → 获取天气并更新按键图片。

---

## 🛠️ 常见问题

### Q: 前端显示空白/默认值？
- 检查 `config.json` 是否存在且格式正确。
- 打开属性检查器的开发者工具（F12），查看 Console 是否有错误。
- 确保后端日志中有 `[Weather] 已同步配置到 StreamDock 存储`。

### Q: 天气图标显示为方块？
- 确保 `resources/iconfont.ttf` 存在且未损坏。
- 检查 `WEATHER_ICON_MAP` 中的 Unicode 是否与字体文件匹配。

### Q: API Key 无效 (`INVALID_USER_KEY`)？
- 确保 Key 是 **Web 服务** 类型，并已启用“天气查询”服务。
- 在属性检查器中重新输入并保存，或直接修改 `config.json`。

### Q: 文字显示很粗/有双边框？
- 检查 `textColor` 和 `strokeColor` 是否设为了相同颜色。若相同，插件会自动跳过描边绘制，仅显示纯色文字。
- 若希望保留边框，请设置不同的颜色。

### Q: 打包后插件无法启动？
- 检查 `manifest.json` 中 `CodePath` 是否为 `WeatherPlugin.exe`。
- 确保 `resources/` 和 `property_inspector/` 文件夹与 exe 同级。
- 查看 Windows 事件日志或杀毒软件隔离区。

---

## 📜 许可证

本项目基于 **MIT 许可证** 开源，可自由使用、修改和分发。

> MIT 许可证要求派生作品必须保留原始的版权声明和许可声明，因此本项目采用 MIT 许可证以保持合规性，并最大程度地促进协作和代码复用。

---

## 🙏 致谢

- [StreamDock 官方 SDK](https://github.com/MiraboxSpace/StreamDock-Plugin-SDK)
- [高德开放平台](https://lbs.amap.com/)
- [iconfont](https://www.iconfont.cn/) 图标库

---

**Happy coding!** 🌤️
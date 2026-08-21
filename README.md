# StreamDock 多功能插件合集

> 一套开箱即用的 StreamDock 插件集，涵盖音乐控制、模拟时钟、实时天气，基于 Python 开发，即插即用。

---

## 🎯 项目简介

本项目包含三款独立实用的 StreamDock 插件，无需复杂配置即可快速上手。

| 插件 | 核心功能 | 适用场景 |
|:---|:---|:---|
| 🎵 **音乐控制** | 实时显示歌曲名，一键播放/暂停，智能滚动 | 游戏、办公、直播 |
| 🕐 **模拟时钟** | 指针表盘，每秒自动刷新 | 桌面装饰、时间提醒 |
| 🌤️ **高德天气** | 实时天气，自定义背景与文字样式 | 出行、直播信息展示 |

---

## ✨ 共同特性

- 🚀 即插即用，无需配置（天气插件需 API Key）
- 🐍 全 Python 3.9+ 开发，开源可二次开发
- 🎨 支持自定义背景、颜色、字体
- 🔒 本地运行，隐私安全（天气插件需联网）
- 📦 提供一键打包脚本（`build.bat`）

---

## 📦 插件详情

### 1. 🎵 音乐控制插件
- **功能**：自动识别 QQ音乐、网易云、Spotify、网页音乐等；显示歌曲名和歌手；播放时滚动，暂停时静止；一键播放/暂停。
- **安装**：复制 `MusicPlugin` 到 StreamDock 插件目录（`%APPDATA%\HotSpot\StreamDock\plugins\`），重启即可。
- **配置**：无需配置，可替换 `icon.png` 自定义背景。

### 2. 🕐 模拟时钟插件
- **功能**：绘制带有时针、分针、秒针的表盘，每秒刷新；支持自定义背景图（500×500）；点击按键手动刷新。
- **安装**：复制 `com.qxb.clock.sdPlugin` 到插件目录，重启，拖拽“时钟”动作到按键。
- **配置**：无需配置，放置 `background.png` 可替换背景。

### 3. 🌤️ 高德天气插件
- **功能**：通过高德 API 获取实时天气；可显示城市、温度、天气描述；自定义字体大小/颜色/描边，背景图或纯色；每 30 分钟自动刷新。
- **安装**：复制 `com.qxb.weather.sdPlugin` 到插件目录，重启，拖拽“天气”动作到按键，右键设置 API Key 和城市。
- **配置**：通过属性检查器或直接编辑 `config.json`。

---

## 🔧 技术栈

| 组件 | 技术 |
|:---|:---|
| 语言 | Python 3.9+ |
| 通信 | WebSocket（StreamDock SDK） |
| 图像 | Pillow |
| 打包 | PyInstaller |
| 配置 | JSON |

---

## 🚀 快速开始

1. 选择所需插件文件夹，复制到 `%APPDATA%\HotSpot\StreamDock\plugins\`。
2. 重启 StreamDock 软件。
3. 在主界面将对应动作拖拽到按键。
4. 天气插件需额外配置 API Key（在属性检查器中设置）。

---

## 🛠️ 开发与调试

- **无硬件测试**：进入插件目录，执行 `python main.py`。
- **查看日志**：`logs/plugin.log`。
- **打包**：运行 `build.bat`，生成 exe 位于 `dist/`，复制整个插件文件夹即可。

---

## ❓ 常见问题

**Q：插件不显示内容？**  
A：检查 StreamDock 日志，确认 WebSocket 连接成功；确保 `manifest.json` 中 UUID 和 `CodePath` 正确。

**Q：音乐插件不显示歌名？**  
A：确保有音乐正在播放，且系统媒体控制功能正常（键盘多媒体键可用）。

**Q：天气插件报 `INVALID_USER_KEY`？**  
A：检查高德 Key 是否为 **Web 服务** 类型，并已开启“天气查询”服务。

**Q：文字显示有双边框？**  
A：若 `textColor` 和 `strokeColor` 相同，插件自动取消描边，设不同颜色即可保留边框。

**Q：多个插件能否同时使用？**  
A：可以，互不干扰。

---

## 📜 许可证

- 音乐控制插件：仅供个人学习，禁止商用。
- 时钟插件 & 天气插件：MIT License。

---

## 🙏 致谢

感谢 [StreamDock SDK](https://github.com/MiraboxSpace/StreamDock-Plugin-SDK)、[高德开放平台](https://lbs.amap.com/)、[Pillow](https://python-pillow.org/) 和 [iconfont](https://www.iconfont.cn/)。

---

**让 StreamDock 更强大，让生活更高效。** 🚀

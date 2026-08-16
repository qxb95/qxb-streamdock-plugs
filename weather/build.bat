@echo off
chcp 65001 >nul
echo ====================================
echo 正在打包天气插件 WeatherPlugin ...
echo ====================================

pip install -r requirements.txt
pyinstaller main.spec

if not exist resources (
    echo 警告: resources 文件夹不存在，请创建并放入背景图片和字体！
) else (
    if exist dist\resources rmdir /s /q dist\resources
    xcopy /E /I resources dist\resources
)

if not exist property_inspector (
    echo 警告: property_inspector 文件夹不存在！
) else (
    if exist dist\property_inspector rmdir /s /q dist\property_inspector
    xcopy /E /I property_inspector dist\property_inspector
)

copy manifest.json dist\
if exist config.json copy config.json dist\

echo ====================================
echo 打包完成！
echo 插件目录: dist\
echo 请将 dist 文件夹重命名为 com.qxb.weather.sdPlugin
echo 并复制到 StreamDock 插件目录。
pause
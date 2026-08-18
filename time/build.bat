@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo =============================================
echo   StreamDock 插件打包工具
echo =============================================

:: 读取 UUID
echo [0/5] 从 manifest.json 读取插件基础名称...
if not exist "manifest.json" (
    echo [错误] 未找到 manifest.json 文件！
    pause
    exit /b 1
)

for /f "delims=" %%i in ('powershell -Command "$ErrorActionPreference='Stop'; $j=Get-Content -Path manifest.json -Raw -Encoding UTF8 | ConvertFrom-Json; $uuid=$j.Actions[0].UUID; if ($uuid -match '\.') { $base=$uuid.Substring(0, $uuid.LastIndexOf('.')); Write-Host $base } else { Write-Host ''; exit 1 }"') do set PLUGIN_BASE=%%i

if "%PLUGIN_BASE%"=="" (
    echo [错误] 无法读取 Actions[0].UUID！
    pause
    exit /b 1
)

set PLUGIN_NAME=%PLUGIN_BASE%.sdPlugin
echo 检测到: %PLUGIN_BASE%
echo 插件文件夹: %PLUGIN_NAME%

:: 检查 PyInstaller
echo [1/5] 检查 PyInstaller...
where pyinstaller >nul 2>nul
if %errorlevel% neq 0 (
    echo [错误] 请安装 PyInstaller: pip install pyinstaller
    pause
    exit /b 1
)

:: 打包
echo [2/5] 正在打包...
pyinstaller main.spec --clean --noconfirm
if %errorlevel% neq 0 (
    echo [错误] 打包失败！
    pause
    exit /b 1
)
if not exist "dist\main.exe" (
    echo [错误] 打包产物未找到！
    pause
    exit /b 1
)

:: 创建插件目录
set PLUGIN_DIR=dist\%PLUGIN_NAME%
echo [3/5] 创建插件目录: %PLUGIN_DIR%
if exist "%PLUGIN_DIR%" rd /s /q "%PLUGIN_DIR%"
mkdir "%PLUGIN_DIR%"

copy "dist\main.exe" "%PLUGIN_DIR%\%PLUGIN_NAME%.exe"
copy "manifest.json" "%PLUGIN_DIR%"
if exist "background.png" copy "background.png" "%PLUGIN_DIR%"

:: 修改 CodePath
echo [4/5] 更新 CodePath...
powershell -Command "(Get-Content '%PLUGIN_DIR%\manifest.json') -replace '\"CodePath\": \"main.py\"', '\"CodePath\": \"%PLUGIN_NAME%.exe\"' | Set-Content '%PLUGIN_DIR%\manifest.json'"

echo =============================================
echo   打包完成！
echo   插件位置: %PLUGIN_DIR%
echo =============================================

:: 询问安装
set /p INSTALL="是否自动安装到 StreamDock 插件目录？(y/n): "
if /i "%INSTALL%"=="y" (
    set STREAMDOCK_PLUGINS=%APPDATA%\HotSpot\StreamDock\plugins
    if exist "%STREAMDOCK_PLUGINS%" (
        echo 正在复制到 %STREAMDOCK_PLUGINS% ...
        xcopy /E /I /Y "%PLUGIN_DIR%" "%STREAMDOCK_PLUGINS%\%PLUGIN_NAME%\"
        echo 安装完成！请重启 StreamDock。
    ) else (
        echo [警告] 未找到插件目录，请手动复制。
    )
)

pause
@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo =============================================
echo   StreamDock 插件打包工具
echo =============================================

:: 1. 读取 UUID
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

:: 2. 检查 PyInstaller
echo [1/5] 检查 PyInstaller...
where pyinstaller >nul 2>nul
if %errorlevel% neq 0 (
    echo [错误] 请安装 PyInstaller: pip install pyinstaller
    pause
    exit /b 1
)

:: 3. 打包
echo [2/5] 正在打包...
if not exist "main.spec" (
    echo [错误] 未找到 main.spec 文件！
    pause
    exit /b 1
)
pyinstaller main.spec --clean --noconfirm
if %errorlevel% neq 0 (
    echo [错误] 打包失败！
    pause
    exit /b 1
)

:: 4. 固定 exe 名称（与 main.spec 中的 name 一致）
set EXE_NAME=DemoPlugin
echo [3/5] 输出 exe 名称: %EXE_NAME%.exe

:: 检查产物
if not exist "dist\%EXE_NAME%.exe" (
    echo [错误] 未找到 dist\%EXE_NAME%.exe，打包可能失败！
    pause
    exit /b 1
)

:: 5. 创建插件目录并复制资源
set PLUGIN_DIR=dist\%PLUGIN_NAME%
echo [4/5] 创建插件目录: %PLUGIN_DIR%
if exist "%PLUGIN_DIR%" rd /s /q "%PLUGIN_DIR%"
mkdir "%PLUGIN_DIR%"

:: 复制 exe 并重命名为插件名
copy "dist\%EXE_NAME%.exe" "%PLUGIN_DIR%\%PLUGIN_NAME%.exe"

:: 复制资源（不再复制 src）
echo 复制资源文件...
if exist "background.png" (
    copy "background.png" "%PLUGIN_DIR%\"
    echo 复制 background.png 完成。
) else (
    echo [警告] background.png 不存在，跳过。
)

if exist "manifest.json" (
    copy "manifest.json" "%PLUGIN_DIR%\"
    echo 复制 manifest.json 完成。
) else (
    echo [警告] manifest.json 不存在，跳过。
)

if exist "property_inspector" (
    xcopy /E /I /Y "property_inspector" "%PLUGIN_DIR%\property_inspector\"
    if %errorlevel% equ 0 (
        echo property_inspector 复制完成。
    ) else (
        echo [错误] property_inspector 复制失败，错误码: %errorlevel%
    )
) else (
    echo [警告] property_inspector 目录不存在，跳过。
)

:: 6. 更新 manifest.json 中的 CodePath
echo [5/5] 更新 CodePath...
if exist "%PLUGIN_DIR%\manifest.json" (
    powershell -Command "$ErrorActionPreference='Stop'; $path='%PLUGIN_DIR%\manifest.json'; $content=Get-Content -Path $path -Raw -Encoding UTF8; $content=$content -replace '\"CodePath\":\s*\"[^\"]*\"', '\"CodePath\": \"%PLUGIN_NAME%.exe\"'; $utf8=New-Object System.Text.UTF8Encoding $false; [System.IO.File]::WriteAllText($path, $content, $utf8)"
    echo CodePath 已更新。
) else (
    echo [警告] 未找到 manifest.json，跳过 CodePath 更新。
)

echo =============================================
echo   打包完成！
echo   插件位置: %PLUGIN_DIR%
echo =============================================

:: 7. 询问安装
set /p INSTALL="是否自动安装到 StreamDock 插件目录？(y/n): "
if /i "%INSTALL%"=="y" (
    set STREAMDOCK_PLUGINS=%APPDATA%\HotSpot\StreamDock\plugins
    if exist "%STREAMDOCK_PLUGINS%" (
        echo 正在复制到 %STREAMDOCK_PLUGINS% ...
        xcopy /E /I /Y "%PLUGIN_DIR%" "%STREAMDOCK_PLUGINS%\%PLUGIN_NAME%\" >nul
        echo 安装完成！请重启 StreamDock。
    ) else (
        echo [警告] 未找到插件目录，请手动复制。
    )
)

pause
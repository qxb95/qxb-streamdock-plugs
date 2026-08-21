# -*- mode: python ; coding: utf-8 -*-
import os
from PyInstaller.utils.hooks import collect_submodules

block_cipher = None
spec_dir = os.getcwd()
repo_dir = os.path.dirname(spec_dir)

# 收集所有 winrt 子模块（用于读取标题）
winrt_submodules = collect_submodules('winrt')
# 收集 pycaw 和 comtypes（用于检测播放状态）
pycaw_submodules = collect_submodules('pycaw')
comtypes_submodules = collect_submodules('comtypes')

datas = [
    (os.path.join(spec_dir, 'core'), 'core'),
    (os.path.join(spec_dir, 'actions'), 'actions'),
    (os.path.join(spec_dir, 'icon.png'), '.'),   # 可选背景图片
]

hiddenimports = [
    'streamdock_core',
    'streamdock_core.action',
    'streamdock_core.action_factory',
    'streamdock_core.app',
    'streamdock_core.images',
    'streamdock_core.logger',
    'streamdock_core.paths',
    'streamdock_core.plugin',
    'streamdock_core.timer',
    'core.music_controller',
    'PIL',
    'PIL.Image',
    'PIL.ImageDraw',
    'PIL.ImageFont',
    'asyncio',
    'uuid',
    # winrt（只读标题）
    'winrt',
    'winrt.windows.foundation',
    'winrt.windows.foundation.collections',
    'winrt.windows.media',
    'winrt.windows.media.control',
    'winrt.windows.storage.streams',
    # websocket-client
    'websocket',
    'websocket._core',
    'websocket._abnf',
    'websocket._exceptions',
    'websocket._http',
    'websocket._socket',
    'websocket._ssl_compat',
    'websocket._utils',
    'websocket._app',
    # 音频检测
    'pycaw',
    'comtypes',
] + winrt_submodules + pycaw_submodules + comtypes_submodules

a = Analysis(
    ['main.py'],
    pathex=[spec_dir, repo_dir],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='MusicPlugin',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
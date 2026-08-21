# main.spec
# -*- mode: python ; coding: utf-8 -*-

import os

block_cipher = None

spec_dir = os.getcwd()
repo_dir = os.path.dirname(spec_dir)

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
    'src.core',
    'src.core.renderer',
    'src.actions',
    'src.actions.time',
    'src.actions.custom',
    'PIL',
    'PIL.Image',
    'PIL.ImageDraw',
    'PIL.ImageFont',
    'websocket',
    'websocket._app',
    'websocket._core',
    'websocket._handshake',
    'requests',
]

datas = [
    ('src', 'src'),               # ✅ 将 src 目录复制到打包输出
    ('manifest.json', '.'),
    ('background.png', '.'),
]

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
    name='main',
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
    icon=None,
)
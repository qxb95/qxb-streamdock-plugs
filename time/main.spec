# main.spec
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

hiddenimports = [
    'src.core',
    'src.core.action',
    'src.core.plugin',
    'src.core.logger',
    'src.core.timer',
    'src.core.action_factory',
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
]

a = Analysis(
    ['main.py'],
    pathex=[],
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
# -*- mode: python ; coding: utf-8 -*-
import os

block_cipher = None

a = Analysis(
    ['gui/main.py'],
    pathex=[os.path.abspath('.')],
    binaries=[],
    datas=[
        ('gui/assets/region.json', 'assets'),
        ('gui/assets/region_test.json', 'assets'),
        ('sdk/delete_all_resources.py', 'sdk'),
        ('sdk/runner_core.py', 'sdk'),
    ],
    hiddenimports=[
        'ucloud',
        'ucloud.client',
        'ucloud.core',
        'ucloud.core.auth',
        'ucloud.core.exc',
        'ucloud.services.uhost',
        'ucloud.services.udisk',
        'ucloud.services.vpc',
        'ucloud.services.unet',
        'ucloud.services.ulb',
        'ucloud.services.nlb',
        'ucloud.services.ugn',
        'ucloud.services.uwsc',
        'requests',
    ],
    hookspath=[],
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
    [],
    exclude_binaries=True,
    name='UCloudCleaner',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='UCloudCleaner',
)

app = BUNDLE(
    coll,
    name='UCloudCleaner.app',
    icon=None,
    bundle_identifier='com.ucloud.cleaner',
    info_plist={
        'NSHighResolutionCapable': True,
        'CFBundleShortVersionString': '1.0.0',
        'CFBundleVersion': '1.0.0',
        'LSMinimumSystemVersion': '11.0',
    },
)

# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files, collect_all, copy_metadata
import os
spec_dir = os.path.dirname(os.path.abspath(SPEC))

datas = []
binaries = []
hiddenimports = []

datas += collect_data_files('gradio')
datas += collect_data_files('gradio_client')

# app
datas += collect_data_files('app')
datas += [('app/ui/js', 'app/ui/js'), ('app/ui/css', 'app/ui/css'), ('images/icons', 'images/icons')]

# safehttpx
safehttpx_datas, safehttpx_binaries, safehttpx_hiddenimports = collect_all('safehttpx')
datas += safehttpx_datas
binaries += safehttpx_binaries
hiddenimports += safehttpx_hiddenimports

# groovy
groovy_datas, groovy_binaries, groovy_hiddenimports = collect_all('groovy')
datas += groovy_datas
binaries += groovy_binaries
hiddenimports += groovy_hiddenimports

# genai_prices
datas += copy_metadata('genai_prices')
datas += copy_metadata('pydantic_ai_slim')
# ======================================================

a = Analysis(
    ['main_desktop.py'],
    pathex=[],
    binaries=binaries,          
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=['hooks'],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='SentenceForge',
    debug=True,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(spec_dir, 'images/icons', 'icon-64.ico')
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='SentenceForge',
)
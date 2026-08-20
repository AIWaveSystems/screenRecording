# -*- mode: python ; coding: utf-8 -*-
import os

binaries = []
try:
    import imageio_ffmpeg
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    if ffmpeg_exe and os.path.exists(ffmpeg_exe):
        binaries.append((ffmpeg_exe, '.'))
except Exception:
    pass

datas = []
for recurso in ('logo.ico', '.env'):
    if os.path.exists(recurso):
        datas.append((recurso, '.'))
if os.path.isdir('assets'):
    datas.append(('assets', 'assets'))

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=['pyaudiowpatch'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

splash_image = os.path.join(os.path.abspath('.'), 'assets', 'splash.png')
splash = Splash(
    splash_image,
    binaries=a.binaries,
    datas=a.datas,
    text_pos=(210, 222),
    text_size=9,
    text_color='#a0a0b0',
    text_default='Extrayendo la aplicacion...',
    minify_script=True,
    always_on_top=True,
) if os.path.exists(splash_image) else None

exe_args = [pyz, a.scripts]
if splash is not None:
    exe_args.extend([splash, splash.binaries])
exe_args.extend([a.binaries, a.datas, []])

exe = EXE(
    *exe_args,
    name='ScreenRecorder',
    icon='logo.ico',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

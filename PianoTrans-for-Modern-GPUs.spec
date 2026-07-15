# -*- mode: python ; coding: utf-8 -*-

import os
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules


project_dir = Path(SPECPATH).resolve()
checkpoint = Path(os.environ["PIANOTRANS_CHECKPOINT"]).resolve()
ffmpeg = Path(os.environ["PIANOTRANS_FFMPEG"]).resolve()

if not checkpoint.is_file():
    raise FileNotFoundError(f"Checkpoint not found: {checkpoint}")
if not ffmpeg.is_file():
    raise FileNotFoundError(f"FFmpeg not found: {ffmpeg}")

datas = collect_data_files("librosa")
datas.append((str(checkpoint), "piano_transcription_inference_data"))
binaries = [(str(ffmpeg), "ffmpeg")]

hiddenimports = []
for package in ("audioread", "piano_transcription_inference", "torchlibrosa"):
    hiddenimports.extend(collect_submodules(package))

a = Analysis(
    [str(project_dir / "src" / "pianotrans_modern_gpu.py")],
    pathex=[str(project_dir / "src")],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["IPython", "jupyter", "notebook", "pytest"],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="PianoTrans-for-Modern-GPUs",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="PianoTrans-for-Modern-GPUs-Portable",
)

# PianoTrans for Modern GPUs

A maintained Windows GUI and portable build workflow for the ByteDance
high-resolution piano transcription model. The project moves the original
PianoTrans workflow from its frozen Python 3.7 / PyTorch 1.10 environment to a
modern PyTorch and CUDA runtime that supports NVIDIA Blackwell GPUs.

## Why this project exists

The original Windows package bundled PyTorch 1.10.2 with CUDA 11.3. That build
does not contain kernels for CUDA capability `sm_120`, so it can detect an RTX
50-series GPU but cannot execute the transcription model on it.

This project keeps the same transcription model and checkpoint while updating
the runtime and packaging layer:

- Python 3.10
- PyTorch 2.10.0 with CUDA 12.8
- Native `sm_120` support for RTX 50-series / Blackwell GPUs
- English Tkinter GUI with multi-file queueing
- Portable PyInstaller `onedir` build
- WAV, FLAC, MP3, M4A, AAC, OGG, Opus and common video container support
- JSON diagnostic mode for validating CUDA, the checkpoint and MIDI output

## Repository contents

```text
src/                                Application source
scripts/setup_environment.ps1       Python and CUDA-enabled PyTorch setup
scripts/download_checkpoint.ps1     Checkpoint downloader
assets/                              Local runtime assets (large files ignored)
PianoTrans-for-Modern-GPUs.spec     PyInstaller onedir configuration
build_portable.ps1                  Reproducible Windows build script
```

The repository intentionally does not commit the virtual environment, CUDA
DLLs, FFmpeg executable, model checkpoint or compiled portable folder. Those
files are several gigabytes and are not suitable for normal Git history.

## Requirements

- Windows 10 or Windows 11, 64-bit
- NVIDIA GPU supported by the selected PyTorch CUDA build
- A recent NVIDIA display driver
- Python 3.10 or [uv](https://docs.astral.sh/uv/)
- At least 12 GB of free disk space for environment plus build output
- FFmpeg for compressed audio/video inputs and portable packaging

A separate CUDA Toolkit installation is not required. PyTorch wheels include
their CUDA runtime; the NVIDIA display driver is still required.

## Set up the development environment

Open PowerShell in the repository and run:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup_environment.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\download_checkpoint.ps1
```

For compressed formats, place a Windows `ffmpeg.exe` at:

```text
assets\ffmpeg\ffmpeg.exe
```

You may also keep FFmpeg on `PATH`.

Run the GUI from source:

```powershell
.\.venv\Scripts\python.exe .\src\pianotrans_modern_gpu.py
```

## Use the GUI

1. Start the application.
2. Select one or more audio files with **Add audio files**.
3. Wait until the status line reports that the queue has finished.

Files passed on the command line or dropped onto the packaged EXE are added to
the same queue. MIDI output is written next to each input file:

```text
input.wav -> input.wav.mid
```

The model is designed for piano recordings. For mixed music, isolate a piano
stem in RipX, UVR or another source-separation tool before transcription.

## Build the portable application

After setup, run:

```powershell
powershell -ExecutionPolicy Bypass -File .\build_portable.ps1
```

If FFmpeg is not under `assets`, provide it explicitly:

```powershell
.\build_portable.ps1 -FFmpegPath "C:\Tools\ffmpeg\bin\ffmpeg.exe"
```

The build is created at:

```text
dist\PianoTrans-for-Modern-GPUs-Portable
```

Keep the EXE and `_internal` directory together. Copying only the EXE will not
work. A typical CUDA-enabled portable folder is approximately 5 GB.

## Diagnostic mode

The packaged EXE can verify the GPU build and transcribe a short input without
opening the GUI:

```powershell
PianoTrans-for-Modern-GPUs.exe --verify "C:\Music\piano.wav" --report "C:\Music\report.json"
```

The report includes the PyTorch version, CUDA runtime, GPU name, architecture
list, checkpoint path, output size, MIDI message count and note-on count.

For Blackwell, confirm that it contains:

```text
CUDA available: True
CUDA architectures: [..., 'sm_120']
GPU model ready.
```

## Troubleshooting

- **CUDA is unavailable:** update the NVIDIA driver and verify that the cu128
  PyTorch wheel was installed inside `.venv`.
- **`sm_120` is missing:** a pre-CUDA-12.8 or CPU-only PyTorch build is active.
- **Checkpoint not found:** run `scripts/download_checkpoint.ps1`.
- **Compressed audio cannot be opened:** install FFmpeg or export WAV/FLAC.
- **The MIDI contains extra notes:** improve piano-stem separation before
  transcription; residual instruments and reverb can be detected as notes.

## Credits and licensing

- [PianoTrans GUI](https://github.com/azuwis/pianotrans)
- [ByteDance Piano Transcription](https://github.com/bytedance/piano_transcription)
- [piano-transcription-inference](https://github.com/qiuqiangkong/piano_transcription_inference)
- [PyTorch](https://pytorch.org/)
- [FFmpeg](https://ffmpeg.org/)

Project-authored source is licensed under the [MIT License](LICENSE).
Downloaded models and third-party components retain their respective licenses.

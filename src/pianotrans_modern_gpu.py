from __future__ import annotations

import io
import json
import os
import queue
import sys
import threading
import time
import traceback
from pathlib import Path
from tkinter import BOTH, END, LEFT, X, Button, Frame, Label, StringVar, Tk, filedialog
from tkinter import scrolledtext


APP_TITLE = "PianoTrans for Modern GPUs"
APP_DIR = Path(__file__).resolve().parent
PROJECT_DIR = APP_DIR.parent
RUNTIME_DIR = (
    Path(sys._MEIPASS).resolve()
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS")
    else PROJECT_DIR / "assets"
)
CHECKPOINT = (
    RUNTIME_DIR
    / "piano_transcription_inference_data"
    / "note_F1=0.9677_pedal_F1=0.9186.pth"
)
FFMPEG_DIR = RUNTIME_DIR / "ffmpeg"

if FFMPEG_DIR.is_dir():
    os.environ["PATH"] = str(FFMPEG_DIR) + os.pathsep + os.environ.get("PATH", "")


class TranscriptionEngine:
    def __init__(self) -> None:
        import librosa
        import torch
        from piano_transcription_inference import PianoTranscription, sample_rate

        self.librosa = librosa
        self.torch = torch
        self.sample_rate = sample_rate

        print("-" * 80)
        print(f"PyTorch: {torch.__version__}")
        print(f"CUDA runtime: {torch.version.cuda}")
        print(f"CUDA available: {torch.cuda.is_available()}")
        if not torch.cuda.is_available():
            raise RuntimeError(
                "CUDA is unavailable. Install a recent NVIDIA driver and verify that "
                "the selected PyTorch build supports your GPU architecture."
            )

        self.gpu_name = torch.cuda.get_device_name(0)
        self.cuda_architectures = torch.cuda.get_arch_list()
        print(f"GPU: {self.gpu_name}")
        print(f"CUDA architectures: {self.cuda_architectures}")
        if not CHECKPOINT.is_file():
            raise FileNotFoundError(
                f"Checkpoint not found: {CHECKPOINT}\n"
                "Run scripts/download_checkpoint.ps1 before starting the application."
            )

        self.model = PianoTranscription(
            device="cuda", checkpoint_path=str(CHECKPOINT)
        )
        print("GPU model ready.")
        print("-" * 80)

    def transcribe(self, path: Path) -> tuple[Path, float]:
        if not path.is_file():
            raise FileNotFoundError(f"Input file not found: {path}")

        output_path = Path(str(path) + ".mid")
        print("-" * 80)
        print(f"Transcribe: {path}")
        print(f"Output: {output_path}")

        audio, _ = self.librosa.load(str(path), sr=self.sample_rate, mono=True)
        started = time.perf_counter()
        self.model.transcribe(audio, str(output_path))
        self.torch.cuda.synchronize()
        elapsed = time.perf_counter() - started
        print(f"Transcription time: {elapsed:.3f} seconds")
        return output_path, elapsed


class QueueWriter:
    def __init__(self, ui_events: queue.Queue[tuple[str, str]]) -> None:
        self.ui_events = ui_events

    def write(self, text: str) -> int:
        if text:
            self.ui_events.put(("log", text))
        return len(text)

    def flush(self) -> None:
        return None


class PianoTransApp:
    def __init__(self, root: Tk, initial_files: list[str]) -> None:
        self.root = root
        self.jobs: queue.Queue[Path] = queue.Queue()
        self.ui_events: queue.Queue[tuple[str, str]] = queue.Queue()
        self.engine: TranscriptionEngine | None = None

        root.title(APP_TITLE)
        root.geometry("920x580")
        root.minsize(680, 420)

        top = Frame(root)
        top.pack(fill=X)
        Button(top, text="Add audio files", command=self.choose_files).pack(
            side=LEFT, padx=8, pady=8
        )
        self.status = StringVar(value="Initializing CUDA and the transcription model...")
        Label(top, textvariable=self.status, anchor="w").pack(
            side=LEFT, fill=X, expand=True, padx=8
        )

        self.textbox = scrolledtext.ScrolledText(root, wrap="word")
        self.textbox.pack(expand=True, fill=BOTH, padx=8, pady=(0, 8))

        writer = QueueWriter(self.ui_events)
        sys.stdout = writer
        sys.stderr = writer
        self.root.after(50, self.drain_ui_events)
        threading.Thread(target=self.worker, daemon=True).start()

        if initial_files:
            self.enqueue(initial_files)
        else:
            self.root.after(250, self.choose_files)

    def drain_ui_events(self) -> None:
        try:
            while True:
                kind, value = self.ui_events.get_nowait()
                if kind == "log":
                    self.textbox.insert(END, value)
                    self.textbox.see(END)
                elif kind == "status":
                    self.status.set(value)
        except queue.Empty:
            pass
        self.root.after(50, self.drain_ui_events)

    def choose_files(self) -> None:
        files = filedialog.askopenfilenames(
            title="Select one or more audio or video files",
            filetypes=[
                (
                    "Audio and video",
                    "*.wav *.flac *.mp3 *.m4a *.aac *.ogg *.opus *.mp4 *.mkv *.mov",
                ),
                ("All files", "*.*"),
            ],
        )
        if files:
            self.enqueue(list(files))

    def enqueue(self, files: list[str]) -> None:
        for value in files:
            path = Path(value).expanduser().resolve()
            print(f"Queue: {path}")
            self.jobs.put(path)
        self.ui_events.put(
            ("status", f"{self.jobs.qsize()} file(s) waiting in the queue")
        )

    def worker(self) -> None:
        try:
            self.engine = TranscriptionEngine()
            self.ui_events.put(("status", f"GPU model ready on {self.engine.gpu_name}"))

            while True:
                path = self.jobs.get()
                try:
                    self.ui_events.put(("status", f"Transcribing: {path.name}"))
                    self.engine.transcribe(path)
                except Exception:
                    traceback.print_exc()
                finally:
                    self.jobs.task_done()
                    remaining = self.jobs.qsize()
                    if remaining:
                        self.ui_events.put(
                            ("status", f"{remaining} file(s) remaining in the queue")
                        )
                    else:
                        self.ui_events.put(
                            ("status", "Queue finished. You can add more files.")
                        )
                        print("-" * 80)
                        print("Queue finished.")
                        print("-" * 80)
        except Exception:
            traceback.print_exc()
            self.ui_events.put(
                ("status", "Initialization failed. See the error log below.")
            )


def verify_portable(input_path: Path, report_path: Path) -> int:
    captured = io.StringIO()
    original_stdout = sys.stdout
    original_stderr = sys.stderr
    sys.stdout = captured
    sys.stderr = captured
    report: dict[str, object] = {
        "success": False,
        "input": str(input_path.resolve()),
        "report": str(report_path.resolve()),
    }

    try:
        import mido

        engine = TranscriptionEngine()
        output_path, elapsed = engine.transcribe(input_path.resolve())
        midi = mido.MidiFile(output_path)
        messages = [message for track in midi.tracks for message in track]
        note_on_events = sum(
            1
            for message in messages
            if message.type == "note_on" and getattr(message, "velocity", 0) > 0
        )
        report.update(
            {
                "success": True,
                "torch_version": engine.torch.__version__,
                "cuda_runtime": engine.torch.version.cuda,
                "cuda_available": engine.torch.cuda.is_available(),
                "gpu": engine.gpu_name,
                "cuda_architectures": engine.cuda_architectures,
                "checkpoint": str(CHECKPOINT),
                "output": str(output_path),
                "output_size": output_path.stat().st_size,
                "midi_messages": len(messages),
                "note_on_events": note_on_events,
                "transcription_seconds": round(elapsed, 3),
            }
        )
        exit_code = 0
    except Exception as error:
        traceback.print_exc()
        report.update({"error_type": type(error).__name__, "error": str(error)})
        exit_code = 1
    finally:
        report["log"] = captured.getvalue()
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            json.dumps(report, indent=2, ensure_ascii=True), encoding="utf-8"
        )
        sys.stdout = original_stdout
        sys.stderr = original_stderr

    return exit_code


def parse_verify_arguments(arguments: list[str]) -> tuple[Path, Path] | None:
    if not arguments or arguments[0] != "--verify":
        return None
    if len(arguments) != 4 or arguments[2] != "--report":
        raise ValueError(
            "Diagnostic usage: PianoTrans-for-Modern-GPUs.exe "
            "--verify INPUT --report REPORT.json"
        )
    return Path(arguments[1]), Path(arguments[3])


def main() -> int:
    arguments = sys.argv[1:]
    try:
        verify_arguments = parse_verify_arguments(arguments)
    except ValueError:
        return 2

    if verify_arguments:
        return verify_portable(*verify_arguments)

    root = Tk()
    PianoTransApp(root, arguments)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

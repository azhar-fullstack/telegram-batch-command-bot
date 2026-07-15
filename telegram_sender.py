#!/usr/bin/env python3
"""Windows desktop automation: paste generated /concept blocks into Telegram."""

from __future__ import annotations

import json
import queue
import threading
import time
import tkinter as tk
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, ttk

import pyautogui
import pyperclip

from command_generator import ConceptRow, load_concepts_from_file, split_command_block

APP_DIR = Path(__file__).resolve().parent
PROGRESS_FILE = APP_DIR / "sender_progress.json"
LOG_FILE = APP_DIR / "sender.log"

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.05


@dataclass
class ProgressState:
    tsv_path: str
    current_row: int = 0
    current_command: int = 0
    send_mode: str = "block"
    cooldown_seconds: float = 3.0
    countdown_seconds: int = 5
    updated_at: str = ""

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2)

    @classmethod
    def from_dict(cls, data: dict) -> ProgressState:
        return cls(
            tsv_path=data.get("tsv_path", ""),
            current_row=int(data.get("current_row", 0)),
            current_command=int(data.get("current_command", 0)),
            send_mode=data.get("send_mode", "block"),
            cooldown_seconds=float(data.get("cooldown_seconds", 3.0)),
            countdown_seconds=int(data.get("countdown_seconds", 5)),
            updated_at=data.get("updated_at", ""),
        )


class TelegramSenderApp:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("Telegram Batch Command Sender")
        self.root.geometry("920x720")
        self.root.minsize(820, 640)

        self.concepts: list[ConceptRow] = []
        self.tsv_path = tk.StringVar()
        self.cooldown = tk.DoubleVar(value=3.0)
        self.countdown = tk.IntVar(value=5)
        self.send_mode = tk.StringVar(value="block")
        self.status_text = tk.StringVar(value="Idle")
        self.progress_text = tk.StringVar(value="No file loaded")

        self._worker: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        self._pause_event.set()
        self._ui_queue: queue.Queue[tuple[str, object]] = queue.Queue()

        self._build_ui()
        self.root.after(100, self._poll_ui_queue)
        self._load_saved_progress()

    def _build_ui(self) -> None:
        pad = {"padx": 10, "pady": 6}

        file_frame = ttk.LabelFrame(self.root, text="Data file")
        file_frame.pack(fill="x", **pad)

        ttk.Entry(file_frame, textvariable=self.tsv_path).pack(
            side="left", fill="x", expand=True, padx=(10, 6), pady=10
        )
        ttk.Button(file_frame, text="Browse TSV/CSV...", command=self._browse_file).pack(
            side="left", padx=(0, 6), pady=10
        )
        ttk.Button(file_frame, text="Load", command=self._load_file).pack(
            side="left", padx=(0, 10), pady=10
        )

        settings = ttk.LabelFrame(self.root, text="Settings")
        settings.pack(fill="x", **pad)

        ttk.Label(settings, text="Cooldown (sec):").grid(row=0, column=0, sticky="w", padx=10, pady=8)
        ttk.Spinbox(
            settings,
            from_=0.5,
            to=120.0,
            increment=0.5,
            textvariable=self.cooldown,
            width=8,
        ).grid(row=0, column=1, sticky="w", pady=8)

        ttk.Label(settings, text="Start countdown (sec):").grid(row=0, column=2, sticky="w", padx=10, pady=8)
        ttk.Spinbox(
            settings,
            from_=0,
            to=30,
            increment=1,
            textvariable=self.countdown,
            width=8,
        ).grid(row=0, column=3, sticky="w", pady=8)

        mode_frame = ttk.Frame(settings)
        mode_frame.grid(row=1, column=0, columnspan=4, sticky="w", padx=10, pady=(0, 8))
        ttk.Label(mode_frame, text="Send mode:").pack(side="left")
        ttk.Radiobutton(
            mode_frame,
            text="One message per row (matches HTML copy)",
            variable=self.send_mode,
            value="block",
        ).pack(side="left", padx=(8, 16))
        ttk.Radiobutton(
            mode_frame,
            text="One message per /concept command (split on ;;;)",
            variable=self.send_mode,
            value="split",
        ).pack(side="left")

        ttk.Label(
            settings,
            text="Before Start: click the Telegram chat input, then leave that window focused.",
            foreground="#555",
        ).grid(row=2, column=0, columnspan=4, sticky="w", padx=10, pady=(0, 8))

        controls = ttk.Frame(self.root)
        controls.pack(fill="x", **pad)

        self.btn_start = ttk.Button(controls, text="Start", command=self._start)
        self.btn_start.pack(side="left", padx=(10, 6))
        self.btn_pause = ttk.Button(controls, text="Pause", command=self._pause, state="disabled")
        self.btn_pause.pack(side="left", padx=6)
        self.btn_resume = ttk.Button(controls, text="Resume", command=self._resume, state="disabled")
        self.btn_resume.pack(side="left", padx=6)
        self.btn_stop = ttk.Button(controls, text="Stop", command=self._stop, state="disabled")
        self.btn_stop.pack(side="left", padx=6)
        ttk.Button(controls, text="Reset progress", command=self._reset_progress).pack(side="left", padx=6)
        ttk.Button(controls, text="Preview selected row", command=self._preview_current).pack(
            side="left", padx=6
        )

        status_frame = ttk.LabelFrame(self.root, text="Progress")
        status_frame.pack(fill="x", **pad)

        ttk.Label(status_frame, textvariable=self.status_text, font=("Segoe UI", 10, "bold")).pack(
            anchor="w", padx=10, pady=(8, 2)
        )
        ttk.Label(status_frame, textvariable=self.progress_text).pack(anchor="w", padx=10, pady=(0, 8))
        self.progress_bar = ttk.Progressbar(status_frame, mode="determinate")
        self.progress_bar.pack(fill="x", padx=10, pady=(0, 10))

        preview_frame = ttk.LabelFrame(self.root, text="Current command preview")
        preview_frame.pack(fill="both", expand=True, **pad)
        self.preview = scrolledtext.ScrolledText(preview_frame, height=12, font=("Consolas", 10))
        self.preview.pack(fill="both", expand=True, padx=10, pady=10)

        log_frame = ttk.LabelFrame(self.root, text="Log")
        log_frame.pack(fill="both", expand=True, **pad)
        self.log_box = scrolledtext.ScrolledText(log_frame, height=8, font=("Consolas", 9))
        self.log_box.pack(fill="both", expand=True, padx=10, pady=10)

    def _log(self, message: str) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")
        line = f"[{timestamp}] {message}\n"
        self.log_box.insert("end", line)
        self.log_box.see("end")
        with LOG_FILE.open("a", encoding="utf-8") as fh:
            fh.write(line)

    def _set_status(self, text: str) -> None:
        self.status_text.set(text)

    def _update_progress_ui(self, row_index: int) -> None:
        total = len(self.concepts)
        if total == 0:
            self.progress_text.set("No rows loaded")
            self.progress_bar["value"] = 0
            return
        current = min(row_index + 1, total)
        concept = self.concepts[row_index]
        self.progress_text.set(
            f"Row {current}/{total} — {concept.name} ({concept.type})"
        )
        self.progress_bar["maximum"] = total
        self.progress_bar["value"] = current
        self.preview.delete("1.0", "end")
        self.preview.insert("1.0", concept.commands)

    def _browse_file(self) -> None:
        path = filedialog.askopenfilename(
            title="Select TSV or CSV file",
            initialdir=str(APP_DIR),
            filetypes=[
                ("Tab/Comma files", "*.tsv *.csv"),
                ("All files", "*.*"),
            ],
        )
        if path:
            self.tsv_path.set(path)

    def _load_file(self) -> None:
        path = self.tsv_path.get().strip()
        if not path:
            messagebox.showwarning("No file", "Choose a TSV or CSV file first.")
            return
        try:
            self.concepts = load_concepts_from_file(path)
        except Exception as exc:
            messagebox.showerror("Load failed", str(exc))
            self._log(f"ERROR loading file: {exc}")
            return
        self._log(f"Loaded {len(self.concepts)} command blocks from {path}")
        self._update_progress_ui(0)
        self._set_status("Ready")

    def _load_saved_progress(self) -> None:
        if not PROGRESS_FILE.exists():
            return
        try:
            data = json.loads(PROGRESS_FILE.read_text(encoding="utf-8"))
            state = ProgressState.from_dict(data)
            self.tsv_path.set(state.tsv_path)
            self.cooldown.set(state.cooldown_seconds)
            self.countdown.set(state.countdown_seconds)
            self.send_mode.set(state.send_mode)
            if state.tsv_path and Path(state.tsv_path).exists():
                self.concepts = load_concepts_from_file(state.tsv_path)
                row = min(state.current_row, max(len(self.concepts) - 1, 0))
                self._update_progress_ui(row)
                self._log(
                    f"Restored progress: row {row + 1}/{len(self.concepts)} "
                    f"(saved {state.updated_at})"
                )
                self._set_status("Progress restored — review and press Start to continue")
        except Exception as exc:
            self._log(f"Could not restore progress: {exc}")

    def _save_progress(self, row_index: int, command_index: int = 0) -> None:
        state = ProgressState(
            tsv_path=self.tsv_path.get().strip(),
            current_row=row_index,
            current_command=command_index,
            send_mode=self.send_mode.get(),
            cooldown_seconds=float(self.cooldown.get()),
            countdown_seconds=int(self.countdown.get()),
            updated_at=datetime.now().isoformat(timespec="seconds"),
        )
        PROGRESS_FILE.write_text(state.to_json(), encoding="utf-8")

    def _reset_progress(self) -> None:
        if self._worker and self._worker.is_alive():
            messagebox.showwarning("Busy", "Stop the sender before resetting progress.")
            return
        if PROGRESS_FILE.exists():
            PROGRESS_FILE.unlink()
        self._log("Progress reset.")
        self._set_status("Progress reset")

    def _set_running_buttons(self, running: bool, paused: bool = False) -> None:
        self.btn_start["state"] = "disabled" if running else "normal"
        self.btn_pause["state"] = "normal" if running and not paused else "disabled"
        self.btn_resume["state"] = "normal" if running and paused else "disabled"
        self.btn_stop["state"] = "normal" if running else "disabled"

    def _start(self) -> None:
        if self._worker and self._worker.is_alive():
            messagebox.showinfo("Running", "Sender is already running.")
            return
        if not self.concepts:
            self._load_file()
        if not self.concepts:
            messagebox.showwarning("No data", "Load a TSV/CSV file with valid rows first.")
            return

        start_row = 0
        start_command = 0
        if PROGRESS_FILE.exists():
            try:
                state = ProgressState.from_dict(
                    json.loads(PROGRESS_FILE.read_text(encoding="utf-8"))
                )
                if Path(state.tsv_path).resolve() == Path(self.tsv_path.get()).resolve():
                    start_row = state.current_row
                    start_command = state.current_command
            except Exception:
                pass

        self._stop_event.clear()
        self._pause_event.set()
        self._set_running_buttons(True)

        self._worker = threading.Thread(
            target=self._run_worker,
            args=(start_row, start_command, self._read_run_settings()),
            daemon=True,
        )
        self._worker.start()

    def _read_run_settings(self) -> dict[str, float | int | str]:
        """Read UI settings on the main thread before starting the worker."""
        self.root.focus_set()
        self.root.update_idletasks()
        try:
            cooldown = float(self.cooldown.get())
        except (tk.TclError, ValueError):
            cooldown = 3.0
        try:
            countdown = int(self.countdown.get())
        except (tk.TclError, ValueError):
            countdown = 5
        return {
            "cooldown": max(0.5, cooldown),
            "countdown": max(0, countdown),
            "send_mode": self.send_mode.get(),
        }

    def _pause(self) -> None:
        self._pause_event.clear()
        self._set_running_buttons(True, paused=True)
        self._ui_queue.put(("status", "Paused"))
        self._log("Paused.")

    def _resume(self) -> None:
        self._pause_event.set()
        self._set_running_buttons(True, paused=False)
        self._ui_queue.put(("status", "Running"))
        self._log("Resumed.")

    def _stop(self) -> None:
        self._stop_event.set()
        self._pause_event.set()
        self._log("Stop requested...")

    def _preview_current(self) -> None:
        if not self.concepts:
            messagebox.showinfo("Preview", "Load a file first.")
            return
        row = 0
        if PROGRESS_FILE.exists():
            try:
                state = ProgressState.from_dict(
                    json.loads(PROGRESS_FILE.read_text(encoding="utf-8"))
                )
                row = min(state.current_row, len(self.concepts) - 1)
            except Exception:
                pass
        self._update_progress_ui(row)

    def _wait_if_paused_or_stopped(self) -> bool:
        while not self._pause_event.is_set():
            if self._stop_event.is_set():
                return False
            time.sleep(0.1)
        return not self._stop_event.is_set()

    def _sleep_cooldown(self, seconds: float) -> bool:
        """Wait between sends. Returns False if stopped."""
        if seconds <= 0:
            return True
        whole = int(seconds)
        fraction = seconds - whole
        for remaining in range(whole, 0, -1):
            if not self._wait_if_paused_or_stopped():
                return False
            self._ui_queue.put(("status", f"Cooldown: {remaining}s remaining"))
            time.sleep(1)
        if fraction > 0:
            if not self._wait_if_paused_or_stopped():
                return False
            time.sleep(fraction)
        return True

    def _paste_and_send(self, text: str) -> None:
        pyperclip.copy(text)
        time.sleep(0.15)
        pyautogui.hotkey("ctrl", "v")
        time.sleep(0.2)
        pyautogui.press("enter")

    def _run_worker(
        self,
        start_row: int,
        start_command: int,
        settings: dict[str, float | int | str],
    ) -> None:
        try:
            countdown = int(settings["countdown"])
            cooldown = float(settings["cooldown"])
            mode = str(settings["send_mode"])

            self._ui_queue.put(
                ("log", f"Run settings: mode={mode}, cooldown={cooldown}s, countdown={countdown}s")
            )
            self._ui_queue.put(("status", f"Starting in {countdown}s — focus Telegram now"))

            self._ui_queue.put(("log", f"Countdown {countdown}s. Click Telegram chat input."))

            for remaining in range(countdown, 0, -1):
                if self._stop_event.is_set():
                    self._ui_queue.put(("status", "Stopped"))
                    self._ui_queue.put(("done", None))
                    return
                self._ui_queue.put(("status", f"Starting in {remaining}s — focus Telegram"))
                time.sleep(1)

            total = len(self.concepts)
            for row_idx in range(start_row, total):
                if not self._wait_if_paused_or_stopped():
                    break

                concept = self.concepts[row_idx]
                self._ui_queue.put(("progress", row_idx))
                self._ui_queue.put(("status", "Running"))
                self._ui_queue.put(
                    ("log", f"Sending row {row_idx + 1}/{total}: {concept.name}")
                )

                if mode == "split":
                    commands = split_command_block(concept.commands)
                    cmd_start = start_command if row_idx == start_row else 0
                    for cmd_idx, command in enumerate(commands[cmd_start:], start=cmd_start):
                        if not self._wait_if_paused_or_stopped():
                            self._save_progress(row_idx, cmd_idx)
                            raise StopIteration
                        self._paste_and_send(command)
                        self._save_progress(row_idx, cmd_idx + 1)
                        self._ui_queue.put(
                            ("log", f"  sent command {cmd_idx + 1}/{len(commands)}")
                        )
                        if cmd_idx < len(commands) - 1:
                            self._ui_queue.put(("log", f"  waiting {cooldown}s..."))
                            if not self._sleep_cooldown(cooldown):
                                self._save_progress(row_idx, cmd_idx + 1)
                                raise StopIteration
                    self._save_progress(row_idx + 1, 0)
                    start_command = 0
                else:
                    self._paste_and_send(concept.commands.rstrip())
                    self._save_progress(row_idx + 1, 0)
                    self._ui_queue.put(("log", "  sent full block"))

                if row_idx < total - 1:
                    self._ui_queue.put(("log", f"Waiting {cooldown}s before next row..."))
                    if not self._sleep_cooldown(cooldown):
                        break

            if self._stop_event.is_set():
                self._ui_queue.put(("status", "Stopped"))
                self._ui_queue.put(("log", "Run stopped by user."))
            else:
                self._ui_queue.put(("status", "Completed"))
                self._ui_queue.put(("log", f"Finished all {total} rows."))
                if PROGRESS_FILE.exists():
                    PROGRESS_FILE.unlink()
                    self._ui_queue.put(("log", "Progress file cleared."))

        except pyautogui.FailSafeException:
            self._ui_queue.put(("status", "Failsafe triggered"))
            self._ui_queue.put(
                ("log", "FAILSAFE: mouse moved to corner. Progress saved.")
            )
        except StopIteration:
            self._ui_queue.put(("status", "Stopped"))
        except Exception as exc:
            self._ui_queue.put(("status", "Error"))
            self._ui_queue.put(("log", f"ERROR: {exc}"))
        finally:
            self._ui_queue.put(("done", None))

    def _poll_ui_queue(self) -> None:
        while True:
            try:
                kind, payload = self._ui_queue.get_nowait()
            except queue.Empty:
                break
            if kind == "log":
                self._log(str(payload))
            elif kind == "status":
                self._set_status(str(payload))
            elif kind == "progress":
                self._update_progress_ui(int(payload))
            elif kind == "done":
                self._set_running_buttons(False)
        self.root.after(100, self._poll_ui_queue)

    def run(self) -> None:
        self.root.mainloop()


def main() -> None:
    TelegramSenderApp().run()


if __name__ == "__main__":
    main()

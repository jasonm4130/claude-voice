"""Push-to-talk dictation: hold a hotkey, speak, release, and the text is pasted where you type.

Third-party imports stay inside functions so `claude-voice --help` and the tests run without the
`listen` extra.
"""

import math
import os
import queue
import re
import sys
import threading
import time

SAMPLE_RATE = 16_000
DEFAULT_MODEL = "mlx-community/Qwen3-ASR-0.6B-6bit"
DEFAULT_HOTKEY = "alt_r"
FRAME_SECONDS = 0.03
FLOOR_DB = -45.0
BELOW_PEAK_DB = 35.0
MIN_SPEECH_SECONDS = 0.2
PAD_SECONDS = 0.15
PASTE_SETTLE_SECONDS = 0.3  # the target app reads the clipboard after Cmd-V returns

ALIASES = {
    "right_option": "alt_r",
    "right_alt": "alt_r",
    "left_option": "alt_l",
    "option": "alt",
    "right_command": "cmd_r",
    "right_cmd": "cmd_r",
    "command": "cmd",
    "right_control": "ctrl_r",
    "right_ctrl": "ctrl_r",
    "control": "ctrl",
    "right_shift": "shift_r",
}

NO_EXTRA = "push to talk needs the listen extra: uv sync --extra listen"
MIC_HINT = (
    "the clip is pure silence: grant Microphone access to this terminal in "
    "System Settings > Privacy & Security > Microphone, then restart it"
)
INPUT_HINT = (
    "cannot watch the keyboard: add this terminal under System Settings > Privacy & Security > "
    "Accessibility and Input Monitoring, then restart it"
)


def stt_model() -> str:
    return os.environ.get("CLAUDE_VOICE_STT_MODEL") or DEFAULT_MODEL


def parse_hotkey(spec: str | None) -> tuple[str, ...]:
    """Turn "right_option" or "ctrl+alt_r" into pynput key names."""
    parts = [p.strip().lower() for p in (spec or DEFAULT_HOTKEY).split("+")]
    if not all(parts):
        raise ValueError(f"bad hotkey: {spec!r}")
    return tuple(ALIASES.get(p, p) for p in parts)


class HotkeyState:
    """Hold-to-talk over a key combo. Any other key during the hold cancels, so Option-chords still type."""

    def __init__(self, keys: tuple[str, ...]):
        self.keys = set(keys)
        self.down: set[str] = set()
        self.active = False

    def press(self, name: str) -> str | None:
        if name not in self.keys:
            if self.active:
                self.active = False
                return "cancel"
            return None
        self.down.add(name)
        if not self.active and self.down == self.keys:
            self.active = True
            return "start"
        return None

    def release(self, name: str) -> str | None:
        self.down.discard(name)
        if self.active and name in self.keys:
            self.active = False
            return "stop"
        return None


def speech_span(levels_db: list[float]) -> tuple[int, int] | None:
    """First and last frame index of speech, or None when there is too little of it."""
    if not levels_db:
        return None
    threshold = max(FLOOR_DB, max(levels_db) - BELOW_PEAK_DB)
    voiced = [i for i, level in enumerate(levels_db) if level >= threshold]
    if len(voiced) * FRAME_SECONDS < MIN_SPEECH_SECONDS:
        return None
    return voiced[0], voiced[-1]


def trim_silence(samples, rate: int = SAMPLE_RATE):
    """Cut leading and trailing silence from mono float audio; None if there is no speech."""
    import numpy as np

    frame = int(rate * FRAME_SECONDS)
    count = len(samples) // frame
    if count == 0:
        return None
    rms = np.sqrt(np.mean(np.square(samples[: count * frame].reshape(count, frame)), axis=1))
    span = speech_span([20 * math.log10(max(float(r), 1e-10)) for r in rms])
    if span is None:
        return None
    pad = int(rate * PAD_SECONDS)
    return samples[max(0, span[0] * frame - pad) : min(len(samples), (span[1] + 1) * frame + pad)]


def clean_text(text: str) -> str:
    # A pasted newline would submit the prompt in some apps; the user presses Enter, not us.
    return re.sub(r"\s+", " ", text).strip()


def cached(model_id: str) -> str:
    """The local snapshot if there is one, so later starts make no network calls."""
    from huggingface_hub import snapshot_download

    try:
        return snapshot_download(model_id, local_files_only=True)
    except Exception:
        return model_id


class Transcriber:
    def __init__(self, model_id: str | None = None):
        from mlx_audio.stt import load

        self.model = load(cached(model_id or stt_model()))

    def __call__(self, samples) -> str:
        if len(samples) < SAMPLE_RATE * MIN_SPEECH_SECONDS:
            return ""
        if not samples.any():
            print(MIC_HINT, file=sys.stderr)
            return ""
        speech = trim_silence(samples)
        if speech is None:
            print("no speech heard", file=sys.stderr)
            return ""
        return clean_text(self.model.generate(speech, language="English").text)


def load_wav(path: str):
    import numpy as np
    from mlx_audio.stt.utils import load_audio

    return np.asarray(load_audio(path, sr=SAMPLE_RATE), dtype=np.float32)


class Recorder:
    """The mic is open only while the key is held, so macOS shows the mic indicator only then."""

    def __init__(self):
        self.chunks: list = []
        self.stream = None

    def start(self) -> None:
        import sounddevice as sd

        self.chunks = []
        self.stream = sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="float32", callback=self._take)
        self.stream.start()

    def _take(self, data, frames, at, status) -> None:
        self.chunks.append(data[:, 0].copy())

    def stop(self):
        import numpy as np

        if self.stream is not None:
            self.stream.stop()
            self.stream.close()
            self.stream = None
        return np.concatenate(self.chunks) if self.chunks else np.zeros(0, dtype=np.float32)


def snapshot(board) -> list[dict]:
    return [{t: item.dataForType_(t) for t in item.types()} for item in board.pasteboardItems() or []]


def restore(board, saved: list[dict]) -> None:
    from AppKit import NSPasteboardItem

    board.clearContents()
    items = []
    for types in saved:
        item = NSPasteboardItem.alloc().init()
        for kind, data in types.items():
            if data is not None:
                item.setData_forType_(data, kind)
        items.append(item)
    if items:
        board.writeObjects_(items)


def paste(text: str, board=None, press=None) -> None:
    """Put text on the clipboard, send Cmd-V, then put the previous clipboard back."""
    from AppKit import NSPasteboard, NSPasteboardItem, NSPasteboardTypeString

    board = board or NSPasteboard.generalPasteboard()
    saved = snapshot(board)
    board.clearContents()
    item = NSPasteboardItem.alloc().init()
    item.setString_forType_(text, NSPasteboardTypeString)
    item.setString_forType_("", "org.nspasteboard.TransientType")  # clipboard managers skip it
    board.writeObjects_([item])
    ours = board.changeCount()
    (press or press_cmd_v)()
    time.sleep(PASTE_SETTLE_SECONDS)
    if board.changeCount() == ours:  # leave it alone if the user copied something meanwhile
        restore(board, saved)


def press_cmd_v() -> None:
    from pynput.keyboard import Controller, Key

    keyboard = Controller()
    with keyboard.pressed(Key.cmd):
        keyboard.tap("v")


def key_name(key) -> str:
    name = getattr(key, "name", None) or getattr(key, "char", None)
    return name.lower() if name else str(key)


def run(events: queue.Queue, recorder, transcribe, insert) -> None:
    """Handle hotkey events until a None arrives. Runs on the thread that loaded the model."""
    from claude_voice.speak import stop_playback

    while (event := events.get()) is not None:
        try:
            if event == "start":
                stop_playback()
                recorder.start()
            elif event == "cancel":
                recorder.stop()
            elif event == "stop":
                text = transcribe(recorder.stop())
                if text:
                    insert(text)
        except Exception as exc:
            print(f"{event}: {type(exc).__name__}: {exc}", file=sys.stderr)


def check_keys(keys: tuple[str, ...]) -> tuple[str, ...]:
    from pynput.keyboard import Key

    for name in keys:
        if len(name) != 1 and name not in Key.__members__:
            raise ValueError(f"unknown key {name!r} in CLAUDE_VOICE_HOTKEY")
    return tuple(name if len(name) == 1 else Key[name].name for name in keys)  # alt_l is reported as alt


def watch_hotkey(keys: tuple[str, ...], events: queue.Queue):
    from pynput import keyboard

    state = HotkeyState(keys)
    lock = threading.Lock()

    def on(handler):
        def callback(key):
            with lock:
                event = handler(key_name(key))
            if event:
                events.put(event)

        return callback

    listener = keyboard.Listener(on_press=on(state.press), on_release=on(state.release))
    listener.start()
    listener.wait()
    return listener


def main(file: str | None = None, do_paste: bool = False) -> int:
    events: queue.Queue = queue.Queue()
    try:
        if not file:
            keys = check_keys(parse_hotkey(os.environ.get("CLAUDE_VOICE_HOTKEY")))
            listener = watch_hotkey(keys, events)
            if not listener.running or not listener.IS_TRUSTED:
                listener.stop()
                print(INPUT_HINT, file=sys.stderr)
                return 1
        transcribe = Transcriber()
    except ImportError:
        print(NO_EXTRA, file=sys.stderr)
        return 1
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 2

    if file:
        text = transcribe(load_wav(file))
        if not text:
            return 1
        print(text)
        if do_paste:
            paste(text)
        return 0

    print(f"listening: hold {'+'.join(keys)} to talk, Ctrl-C to quit", file=sys.stderr)
    try:
        run(events, Recorder(), transcribe, paste)
    except KeyboardInterrupt:
        pass
    finally:
        listener.stop()
    return 0

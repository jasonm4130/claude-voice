"""Speak text with Phonon, replacing anything already playing."""

import argparse
import os
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

CONFIG_DIR = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "claude-voice"
STATE_DIR = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local" / "state")) / "claude-voice"
DEFAULT_VOICE_FILE = CONFIG_DIR / "voice.safetensors"
PID_FILE = STATE_DIR / "player.pid"
LOG_FILE = STATE_DIR / "spoken.log"


def voice_file() -> Path | None:
    path = Path(os.environ.get("CLAUDE_VOICE_FILE", DEFAULT_VOICE_FILE)).expanduser()
    return path if path.is_file() else None


def stop_playback() -> None:
    """Stop the clip a previous call left playing, if any."""
    try:
        pid = int(PID_FILE.read_text())
    except (FileNotFoundError, ValueError):
        return
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    PID_FILE.unlink(missing_ok=True)


def load_tts():
    """Load Phonon and the configured voice; return (tts, voice name or None)."""
    import ptts  # imported late: loading it is the slow part

    tts = ptts.TTS(lang="en")
    custom = voice_file()
    if custom:
        tts.add_voice("custom", str(custom))
        return tts, "custom"
    return tts, os.environ.get("CLAUDE_VOICE_NAME") or None


def speak(text: str) -> None:
    tts, voice = load_tts()

    STATE_DIR.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(suffix=".wav", dir=STATE_DIR, delete=False) as wav:
        wav_path = Path(wav.name)
    try:
        if voice:
            tts.save(str(wav_path), text, voice=voice)
        else:
            tts.save(str(wav_path), text)
        stop_playback()
        with LOG_FILE.open("a") as log:
            log.write(f"{time.strftime('%Y-%m-%dT%H:%M:%S')} {text}\n")
        player = subprocess.Popen(["afplay", str(wav_path)])
        PID_FILE.write_text(str(player.pid))
        player.wait()
        if PID_FILE.exists() and PID_FILE.read_text() == str(player.pid):
            PID_FILE.unlink(missing_ok=True)
    finally:
        wav_path.unlink(missing_ok=True)


def doctor() -> int:
    """Print one line per check; return 1 if any required check fails."""
    import shutil

    ok = True

    def report(passed: bool, label: str, detail: str = "", required: bool = True) -> None:
        nonlocal ok
        mark = "ok  " if passed else ("FAIL" if required else "note")
        ok = ok and (passed or not required)
        print(f"{mark} {label}" + (f": {detail}" if detail else ""))

    report(sys.platform == "darwin", "macOS", sys.platform)
    report(shutil.which("afplay") is not None, "afplay on PATH")
    report(shutil.which("uv") is not None, "uv on PATH")
    report(
        os.environ.get("CLAUDE_VOICE") == "1",
        "CLAUDE_VOICE=1 in this shell",
        "hooks stay silent without it",
        required=False,
    )
    custom = voice_file()
    named = os.environ.get("CLAUDE_VOICE_NAME")
    if custom:
        report(True, "voice", str(custom))
    else:
        report(True, "voice", f"catalog voice {named}" if named else "Phonon default (no voice file found)")

    try:
        start = time.perf_counter()
        tts, voice = load_tts()
        loaded = time.perf_counter() - start
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        wav = STATE_DIR / "doctor.wav"
        start = time.perf_counter()
        kwargs = {"voice": voice} if voice else {}
        seconds = tts.save(str(wav), "Claude voice is working.", **kwargs)
        took = time.perf_counter() - start
        wav.unlink(missing_ok=True)
        report(True, "Phonon", f"loaded in {loaded:.2f} s; {seconds:.1f} s of speech in {took:.2f} s")
    except Exception as exc:  # report, do not crash
        report(False, "Phonon", f"{type(exc).__name__}: {exc}")

    return 0 if ok else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="claude-voice", description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    say = sub.add_parser("say", help="speak text (from arguments or stdin)")
    say.add_argument("text", nargs="*")
    sub.add_parser("stop", help="stop whatever is playing")
    sub.add_parser("doctor", help="check the setup and time a test line")
    args = parser.parse_args(argv)

    if args.cmd == "stop":
        stop_playback()
        return 0
    if args.cmd == "doctor":
        return doctor()
    text = " ".join(args.text) if args.text else sys.stdin.read()
    if text.strip():
        speak(text.strip())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

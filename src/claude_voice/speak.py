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


def speak(text: str) -> None:
    import ptts  # imported late: loading it is the slow part

    tts = ptts.TTS(lang="en")
    voice = None
    custom = voice_file()
    if custom:
        tts.add_voice("custom", str(custom))
        voice = "custom"
    elif os.environ.get("CLAUDE_VOICE_NAME"):
        voice = os.environ["CLAUDE_VOICE_NAME"]

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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="claude-voice", description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    say = sub.add_parser("say", help="speak text (from arguments or stdin)")
    say.add_argument("text", nargs="*")
    sub.add_parser("stop", help="stop whatever is playing")
    args = parser.parse_args(argv)

    if args.cmd == "stop":
        stop_playback()
        return 0
    text = " ".join(args.text) if args.text else sys.stdin.read()
    if text.strip():
        speak(text.strip())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

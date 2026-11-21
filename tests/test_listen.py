import os
import queue
import re
import sys
import uuid

import pytest

from claude_voice import listen
from claude_voice.listen import HotkeyState, clean_text, parse_hotkey, speech_span


def test_parse_hotkey_default_and_aliases():
    assert parse_hotkey(None) == ("alt_r",)
    assert parse_hotkey("Right_Option") == ("alt_r",)
    assert parse_hotkey("ctrl + f13") == ("ctrl", "f13")


@pytest.mark.parametrize("spec", ["+", "ctrl+", " "])
def test_parse_hotkey_rejects_empty_parts(spec):
    with pytest.raises(ValueError):
        parse_hotkey(spec)


def test_stt_model_override(monkeypatch):
    monkeypatch.delenv("CLAUDE_VOICE_STT_MODEL", raising=False)
    assert listen.stt_model() == listen.DEFAULT_MODEL
    monkeypatch.setenv("CLAUDE_VOICE_STT_MODEL", "some/model")
    assert listen.stt_model() == "some/model"


def test_hold_and_release():
    state = HotkeyState(("alt_r",))
    assert state.press("alt_r") == "start"
    assert state.press("alt_r") is None  # key repeat
    assert state.release("alt_r") == "stop"


def test_combo_needs_every_key():
    state = HotkeyState(("ctrl", "f13"))
    assert state.press("ctrl") is None
    assert state.press("f13") == "start"
    assert state.release("ctrl") == "stop"
    assert state.release("f13") is None


def test_other_key_during_hold_cancels():
    state = HotkeyState(("alt_r",))
    state.press("alt_r")
    assert state.press("e") == "cancel"
    assert state.release("alt_r") is None
    assert state.press("e") is None


def test_speech_span():
    quiet, loud = -70.0, -20.0
    levels = [quiet] * 10 + [loud] * 20 + [quiet] * 5
    assert speech_span(levels) == (10, 29)


def test_speech_span_drops_noise_and_blips():
    assert speech_span([]) is None
    assert speech_span([-60.0] * 100) is None  # under the absolute floor
    assert speech_span([-70.0] * 50 + [-20.0] * 3 + [-70.0] * 50) is None  # a click, not speech


def test_clean_text_never_submits():
    assert clean_text("  run the tests\nthen push\r\n") == "run the tests then push"


def test_run_stops_playback_and_inserts(monkeypatch):
    calls = []
    monkeypatch.setattr("claude_voice.speak.stop_playback", lambda: calls.append("stop_playback"))

    class FakeRecorder:
        def start(self):
            calls.append("record")

        def stop(self):
            return "clip"

    events = queue.Queue()
    for event in ["start", "cancel", "start", "stop", None]:
        events.put(event)
    listen.run(events, FakeRecorder(), lambda clip: f"text from {clip}", calls.append)
    assert calls == ["stop_playback", "record", "stop_playback", "record", "text from clip"]


def test_trim_silence():
    np = pytest.importorskip("numpy")
    rate = listen.SAMPLE_RATE
    t = np.arange(rate) / rate
    tone = (0.3 * np.sin(2 * np.pi * 220 * t)).astype(np.float32)
    clip = np.concatenate([np.zeros(rate, np.float32), tone, np.zeros(rate, np.float32)])
    trimmed = listen.trim_silence(clip)
    pad = rate * listen.PAD_SECONDS
    assert len(trimmed) == pytest.approx(rate + 2 * pad, abs=rate * 0.05)
    hiss = (np.random.default_rng(0).standard_normal(rate * 2) * 0.002).astype(np.float32)
    assert listen.trim_silence(hiss) is None


def test_pasteboard_round_trip():
    pytest.importorskip("AppKit")
    from AppKit import NSPasteboard, NSPasteboardTypeString

    board = NSPasteboard.pasteboardWithName_(f"claude-voice-test-{uuid.uuid4()}")
    board.clearContents()
    board.setString_forType_("what the user had", NSPasteboardTypeString)
    seen = []
    listen.paste("dictated", board, press=lambda: seen.append(board.stringForType_(NSPasteboardTypeString)))
    assert seen == ["dictated"]
    assert board.stringForType_(NSPasteboardTypeString) == "what the user had"
    board.releaseGlobally()


def words(text):
    """Score identifiers as spoken: load_model is "load model", speak.py is "speak dot py"."""
    text = re.sub(r"(\w)\.(\w)", r"\1 dot \2", text.lower().replace("_", " "))
    return re.sub(r"[^a-z0-9 ]", " ", text).split()


def wer(ref, hyp):
    r, h = words(ref), words(hyp)
    row = list(range(len(h) + 1))
    for i in range(1, len(r) + 1):
        prev, row[0] = row[0], i
        for j in range(1, len(h) + 1):
            prev, row[j] = row[j], min(row[j] + 1, row[j - 1] + 1, prev + (r[i - 1] != h[j - 1]))
    return row[-1] / len(r)


def test_short_tap_is_ignored_without_a_model(capsys):
    np = pytest.importorskip("numpy")
    transcriber = listen.Transcriber.__new__(listen.Transcriber)  # no model: it must not be reached
    assert transcriber(np.zeros(0, np.float32)) == ""
    assert capsys.readouterr().err == ""


def test_check_keys_uses_reported_names():
    pytest.importorskip("pynput")
    assert listen.check_keys(("alt_l", "alt_r", "e")) == ("alt", "alt_r", "e")
    with pytest.raises(ValueError):
        listen.check_keys(("hyper",))


@pytest.mark.skipif(
    sys.platform != "darwin" or os.environ.get("CLAUDE_VOICE_ROUNDTRIP") != "1",
    reason="downloads models; set CLAUDE_VOICE_ROUNDTRIP=1 on a Mac with the listen extra",
)
def test_round_trip_through_the_listen_loop(tmp_path, monkeypatch):
    """Phonon speaks a line, the worker loop transcribes it as if it came from the mic."""
    pytest.importorskip("mlx_audio")
    import numpy as np
    import ptts

    monkeypatch.setattr("claude_voice.speak.stop_playback", lambda: None)
    lines = [
        "Please run the tests again and tell me which ones still fail.",
        "Rename the function load model to load transcriber and update the call in speak dot py.",
    ]

    class WavRecorder:
        clip = None

        def start(self):
            pass

        def stop(self):
            return self.clip

    tts = ptts.TTS(lang="en")
    transcribe = listen.Transcriber()
    silence = np.zeros(listen.SAMPLE_RATE, np.float32)
    recorder = WavRecorder()
    for i, line in enumerate(lines):
        wav = tmp_path / f"{i}.wav"
        tts.save(str(wav), line)
        recorder.clip = np.concatenate([silence, listen.load_wav(str(wav)), silence])
        got = []
        events = queue.Queue()
        for event in ["start", "stop", None]:
            events.put(event)
        listen.run(events, recorder, transcribe, got.append)
        print(f"heard: {got[0]!r}")
        assert wer(line, got[0]) <= 0.1


def test_cli_help_works_without_the_extra():
    from claude_voice.speak import main

    with pytest.raises(SystemExit) as done:
        main(["listen", "--help"])
    assert done.value.code == 0

import json
import os
import subprocess
import sys
from pathlib import Path

from claude_voice.hook import enabled, text_for

ON = {"CLAUDE_VOICE": "1"}
HOOK = Path(__file__).resolve().parent.parent / "bin" / "hook"


def test_gate():
    assert enabled(ON)
    assert not enabled({})
    assert not enabled({"CLAUDE_VOICE": "true"})


def test_stop_speaks_the_reply():
    event = {"hook_event_name": "Stop", "last_assistant_message": "**Done.** Tests pass."}
    assert text_for(event, ON) == "Done. Tests pass."


def test_stop_respects_max_words():
    event = {"hook_event_name": "Stop", "last_assistant_message": "One two. Three four five."}
    assert text_for(event, {**ON, "CLAUDE_VOICE_MAX_WORDS": "3"}) == "One two."
    assert text_for(event, {**ON, "CLAUDE_VOICE_MAX_WORDS": "junk"}) == "One two. Three four five."


def test_stop_skips_a_continued_stop():
    event = {"hook_event_name": "Stop", "stop_hook_active": True, "last_assistant_message": "Hi."}
    assert text_for(event, ON) == ""


def test_notification_permission_prompt():
    event = {
        "hook_event_name": "Notification",
        "notification_type": "permission_prompt",
        "message": "Claude needs your permission",
    }
    assert text_for(event, ON) == "Claude needs your permission"
    assert text_for(event, {**ON, "CLAUDE_VOICE_NOTIFY": "0"}) == ""


def test_notification_idle_is_silent():
    event = {"hook_event_name": "Notification", "notification_type": "idle_prompt", "message": "Waiting"}
    assert text_for(event, ON) == ""


def test_unknown_event_is_silent():
    assert text_for({"hook_event_name": "PreToolUse"}, ON) == ""


def _run_hook(stdin: str, env: dict[str, str]) -> subprocess.CompletedProcess:
    clean = {k: v for k, v in os.environ.items() if not k.startswith("CLAUDE_VOICE")}
    clean.update(env, PATH="/nonexistent")
    return subprocess.run(
        [sys.executable, str(HOOK)], input=stdin, text=True, env=clean, capture_output=True, timeout=10
    )


def test_hook_script_never_fails():
    for stdin in ["", "not json", json.dumps({"hook_event_name": "Stop", "last_assistant_message": "Hi."})]:
        for env in [{}, ON]:
            result = _run_hook(stdin, env)
            assert result.returncode == 0, (stdin, env, result.stderr)
            assert result.stdout == ""

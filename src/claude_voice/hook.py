"""Decide what a Claude Code hook event should say. Standard library only.

The hook entry point (`bin/hook`) runs under the system Python on every turn,
so this module must import nothing outside the standard library and must
never raise.
"""

import os
from collections.abc import Mapping

from claude_voice.spoken import MAX_WORDS, spoken_text

# Notification types worth interrupting you for. idle_prompt is left out on
# purpose: it fires a minute after every reply and would talk over you.
NOTIFY_TYPES = {"permission_prompt", "elicitation_dialog", "elicitation_url_dialog"}


def enabled(env: Mapping[str, str] | None = None) -> bool:
    env = os.environ if env is None else env
    return env.get("CLAUDE_VOICE") == "1"


def text_for(event: dict, env: Mapping[str, str] | None = None) -> str:
    """Return the line to speak for a hook event, or "" for silence."""
    if env is None:
        env = os.environ
    name = event.get("hook_event_name")

    if name == "Stop":
        if event.get("stop_hook_active"):
            return ""
        return spoken_text(event.get("last_assistant_message") or "", _max_words(env))

    if name == "Notification":
        if env.get("CLAUDE_VOICE_NOTIFY", "1") != "1":
            return ""
        if event.get("notification_type") not in NOTIFY_TYPES:
            return ""
        return (event.get("message") or "").strip()

    return ""


def _max_words(env: Mapping[str, str]) -> int:
    try:
        value = int(env.get("CLAUDE_VOICE_MAX_WORDS") or MAX_WORDS)
    except ValueError:
        return MAX_WORDS
    return value if value > 0 else MAX_WORDS

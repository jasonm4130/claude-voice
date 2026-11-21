# Changelog

## 0.2.0 (2026-11-22)

- Speaks permission prompts and MCP input requests (`Notification` hook). Turn off with `CLAUDE_VOICE_NOTIFY=0`.
- `claude-voice doctor` checks the setup and times a test line.
- `CLAUDE_VOICE_MAX_WORDS` sets the summary length.
- The hook exits cleanly on any input, including a missing `uv`.
- Headings are no longer read aloud.
- Demo clips, a full README and generic research notes.

## 0.1.0 (2026-11-22)

- First release: a `Stop` hook speaks a `<spoken>` block or a short summary with Phonon 31M. Opt in with `CLAUDE_VOICE=1`.

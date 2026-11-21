# AGENTS.md

A Claude Code plugin that speaks a short line when a turn ends or Claude needs you, using the local Phonon TTS model. Read README.md "How it works" before changing what gets said.

## Rules that are easy to break

- **The hook path is standard library only.** `bin/hook`, `src/claude_voice/hook.py` and `src/claude_voice/spoken.py` run under the system `python3` on every turn. They must not import `ptts`, any third-party package, or (in `hook.py`) `speak.py`.
- **The hook never blocks and never fails.** It exits 0 with no stdout on every input, including malformed JSON and a missing `uv`. Speaking happens in a detached child (`start_new_session=True`). `tests/test_hook.py::test_hook_script_never_fails` guards this.
- **Silent unless opted in.** Nothing speaks without `CLAUDE_VOICE=1`; headless runs and teammates share the machine.
- **Say less.** A spoken line is a summary, not a reading. Keep the 35-word default, and add no event that fires every turn; `idle_prompt` is excluded on purpose.
- **Local only.** No network calls beyond the model download `ptts` does itself. No API keys.
- **No voice files in git.** `*.safetensors` and `*.wav` are ignored. Demo clips in `docs/samples/` use catalog voices only.
- **Research is a dated snapshot.** Add a new dated report rather than editing figures in `docs/research/`.

## Layout

- `bin/hook`: hook entry point for `Stop` and `Notification` (wired in `hooks/hooks.json`).
- `src/claude_voice/spoken.py`: turns a reply into a speakable line.
- `src/claude_voice/hook.py`: chooses the line for an event, and applies the gate and settings.
- `src/claude_voice/speak.py`: the `claude-voice` CLI (`say`, `stop`, `doctor`); loads Phonon and plays the audio.
- `.claude-plugin/`: the plugin and marketplace manifests. Bump `version` in both files together.

## Checks

```sh
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

For a change to the speaking path, also run `uv run claude-voice doctor` and one real session (`CLAUDE_VOICE=1 claude --plugin-dir .`), and check the line appears in `~/.local/state/claude-voice/spoken.log`.

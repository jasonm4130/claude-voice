# AGENTS.md

A Claude Code plugin that speaks a short line when a turn ends or Claude needs you, using the local Phonon TTS model. README.md explains the design; read "How it works" before changing what gets said.

## Rules that are easy to break

- **The hook path is standard library only.** `bin/hook`, `src/claude_voice/hook.py` and `src/claude_voice/spoken.py` run under the system `python3` on every turn. They must not import `ptts` or any third-party package, and `hook.py` must not import `speak.py`.
- **The hook never blocks and never fails.** It exits 0 with no stdout on every input, including empty or malformed JSON and a missing `uv`. All speaking happens in a detached child (`start_new_session=True`). `tests/test_hook.py::test_hook_script_never_fails` guards this.
- **Silent unless opted in.** Nothing speaks without `CLAUDE_VOICE=1`. Headless runs and agent teammates share the machine; a default-on change would make them all talk.
- **Say less.** A spoken line is a summary, not a reading. Keep the 35-word default and do not add new events that fire on every turn; `idle_prompt` is excluded on purpose.
- **Local only.** No network calls besides the model download that `ptts` does itself. No API keys.
- **No voice files in git.** `*.safetensors` and `*.wav` are ignored. Demo clips in `docs/samples/` use catalog voices (Apache 2.0) only.
- **Research is a dated snapshot.** Do not update figures in `docs/research/` in place; add a new dated report instead.

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

Before calling a change to the speaking path done, run `uv run claude-voice doctor` and one real session (`CLAUDE_VOICE=1 claude --plugin-dir .`), then check that the line appears in `~/.local/state/claude-voice/spoken.log`.

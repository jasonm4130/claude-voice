# claude-voice

Claude Code says a short version of each reply out loud, on your Mac, in a voice you choose. Nothing leaves the machine: speech comes from [Phonon](https://huggingface.co/gradium/phonon-31m-en), a 31M-parameter local text-to-speech model.

It is a `Stop` hook. When Claude finishes a turn, the hook takes the reply, keeps a `<spoken>…</spoken>` block if there is one, or else strips the markdown and code and keeps the first sentences up to about 35 words. It hands that to a detached speaker and returns at once. A new reply cuts off the one still playing. Each spoken line is logged to `~/.local/state/claude-voice/spoken.log`.

## Requirements

- macOS on Apple Silicon (`afplay` plays the audio)
- [uv](https://docs.astral.sh/uv/)

## Install

```shell
claude plugin marketplace add jasonm4130/claude-voice
claude plugin install claude-voice@claude-voice
```

The first spoken reply downloads the Phonon model (about 65 MB).

## Use

It speaks only in sessions started with `CLAUDE_VOICE=1`, so headless runs and agent teammates stay quiet:

```shell
CLAUDE_VOICE=1 claude
```

Try the voice without Claude:

```shell
uv run claude-voice say "Build passed, two warnings."
uv run claude-voice stop
```

## Choosing a voice

- **Your own voice file.** Design one from a text description in [Gradium Studio](https://studio.gradium.ai/) (Voice Design is free), then choose ⋮ → Download for Phonon. Save it as `~/.config/claude-voice/voice.safetensors`, or point `CLAUDE_VOICE_FILE` at it.
- **A catalog voice.** Set `CLAUDE_VOICE_NAME` to a name from `uvx ptts --list-voices`.
- **Neither.** Phonon's default voice.

Voice files are git-ignored here; keep yours outside the repo.

## Research

`docs/research/` holds the November 2026 survey behind the design: speech-to-text, text-to-speech, Claude Code integration points, language and framework, speech-to-speech, turn-taking, voice UX and local full-duplex models. Figures there are mostly from vendor pages, not measured here.

## Licence

MIT. Phonon 31M English and its voice catalog are Apache 2.0.

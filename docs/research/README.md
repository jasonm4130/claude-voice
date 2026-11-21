# Research notes

Research snapshot, November 2026. Figures are from the cited sources unless marked as measured; nothing here was benchmarked by this project.

These reports survey the options for a local voice layer for Claude Code on an Apple Silicon Mac.

1. [STT models](1-stt-models.md): speech-to-text options. Main conclusion: Qwen3-ASR (1.7B or 0.6B) on MLX per utterance behind Silero VAD or push-to-talk, with Nemotron streaming ASR for live partials and Deepgram Flux as an opt-in cloud fallback; plan on a post-ASR correction step for identifiers.
2. [TTS models](2-tts-models.md): text-to-speech options, local and cloud. Main conclusion: Qwen3-TTS is the best local all-rounder, Phonon 31M is the latency floor, Inworld Realtime TTS-2 Flash is the cloud pick, and text normalisation before TTS is the cheapest big win.
3. [Claude Code integration](3-claude-code-integration.md): hooks, channels, mods, the Agent SDK and prior art. Main conclusion: build a thin custom layer in phases, starting with a `Stop` hook plus a local TTS daemon, then a channel for hands-free input, then an Agent SDK session only if token-level latency or barge-in matters.
4. [Language and framework](4-language-framework.md): Pipecat, LiveKit, Swift and Rust compared. Main conclusion: Python with Pipecat and the Claude Agent SDK, push-to-talk first; echo cancellation on Mac speakers is the biggest practical risk.
5. [Speech-to-speech](5-speech-to-speech.md): whether to skip or augment the cascade. Main conclusion: Claude has no speech API, so cascade now and add acknowledgements and barge-in inside it; a local full-duplex front model is a time-boxed experiment.
6. [Turn-taking and audio](6-turn-taking-audio.md): VAD, end-of-turn detection, barge-in, echo cancellation and mic permissions. Main conclusion: push-to-talk first, then Silero plus Smart Turn v3.2 for hands-free; use headphones or half-duplex by default and VoiceProcessingIO only as an opt-in.
7. [Voice UX](7-voice-ux.md): what to speak, when, and how to approve actions by voice. Main conclusion: speak less in a fixed briefing order, let Claude write a short spoken summary, use earcons for routine events, and never accept a bare spoken "yes" for destructive actions.
8. [Local full-duplex](8-local-full-duplex.md): local full-duplex front models on Mac. Main conclusion: none documents speaking given text verbatim, so use a split front where a duplex model handles conversation and a deterministic TTS path speaks Claude's summaries; NemotronLabs VoiceChat 11B via speech-swift is the top candidate.

## Chosen stack

The project's chosen stack is Phonon 31M for speech and Claude Code hooks for integration. Reports 5 and 8 cover full-duplex speech-to-speech as a possible future direction.

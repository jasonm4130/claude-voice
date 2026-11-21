# Research notes

Snapshot, November 2026. Figures come from the cited sources; nothing here was benchmarked by this project. The reports survey options for a local voice layer for Claude Code on Apple Silicon.

1. [STT models](1-stt-models.md): speech-to-text options. Qwen3-ASR (1.7B or 0.6B) on MLX per utterance, behind Silero VAD or push-to-talk; Nemotron streaming for live partials; Deepgram Flux as an opt-in cloud fallback; correct identifiers after ASR.
2. [TTS models](2-tts-models.md): text-to-speech options, local and cloud. Qwen3-TTS is the best local all-rounder, Phonon 31M the latency floor, Inworld Realtime TTS-2 Flash the cloud pick; normalising text before TTS is the cheapest win.
3. [Claude Code integration](3-claude-code-integration.md): hooks, channels, mods, the Agent SDK and prior art. Build a thin layer in phases: a `Stop` hook plus a local TTS daemon, then a channel for hands-free input, then an Agent SDK session only if token-level latency or barge-in matters.
4. [Language and framework](4-language-framework.md): Pipecat, LiveKit, Swift and Rust compared. Python with Pipecat and the Claude Agent SDK, push-to-talk first; echo cancellation on Mac speakers is the biggest risk.
5. [Speech-to-speech](5-speech-to-speech.md): whether to skip or augment the cascade. Claude has no speech API, so cascade now, adding acknowledgements and barge-in; a local full-duplex front model is a time-boxed experiment.
6. [Turn-taking and audio](6-turn-taking-audio.md): VAD, end-of-turn detection, barge-in, echo cancellation and mic permissions. Push-to-talk first, then Silero plus Smart Turn v3.2 for hands-free; headphones or half-duplex by default, VoiceProcessingIO opt-in.
7. [Voice UX](7-voice-ux.md): what to speak, when, and how to approve actions by voice. Speak less, in a fixed briefing order; let Claude write the summary; earcons for routine events; never accept a bare spoken "yes" for destructive actions.
8. [Local full-duplex](8-local-full-duplex.md): local full-duplex front models on Mac. None documents speaking given text verbatim, so split the front: a duplex model for conversation, deterministic TTS for Claude's summaries. NemotronLabs VoiceChat 11B via speech-swift is the top candidate.

## Chosen stack

Phonon 31M for speech and Claude Code hooks for integration. Reports 5 and 8 cover full-duplex speech-to-speech as a possible future direction.

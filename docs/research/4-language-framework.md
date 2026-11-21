# Language and framework for a "Claude talks to me" voice layer (research, 2026-11-22)

Warning up front: Claude Code already ships `/voice` dictation (hold or tap to talk, input only, no spoken replies), so this project is really the output half plus hands-free input. Ambient already contains a working push-to-talk to agent to spoken-reply path (`ambient talk`) and a Python TTS helper; check that before building anything new. Nothing was installed or run; ambient was read only.

## 1. Framework comparison

| Framework | Local models on Apple Silicon | Claude support / can drive Claude Code | Streaming STT-LLM-TTS | Barge-in | VAD / turn detection | macOS transport | Maturity, licence |
|---|---|---|---|---|---|---|---|
| Pipecat (Python) | Yes: `WhisperSTTServiceMLX` (mlx-whisper), Kokoro, Piper, Moonshine, Ollama services | `pipecat-ai[anthropic]` LLM service (raw Messages API). No Claude Code/Agent SDK service; you would write a custom `FrameProcessor` that calls the Agent SDK | Full frame pipeline, streams everywhere | Built in (interruption frames, user turn strategies) | Silero VAD + Smart Turn v3.2 (ONNX, bundled, default stop strategy since v0.0.102) | `LocalAudioTransport` over PyAudio (no AEC); SmallWebRTC for browser (browser gives AEC) | v1.16.0 on 2026-11-12, very active, BSD-2 |
| Pipecat Flows | n/a (state machine layer on Pipecat) | Same | Same | Same | Same | Same | Overkill for one agent loop |
| LiveKit Agents (Python/Node) | Plugins mostly cloud; local possible via custom STT/TTS plugins, but needs a LiveKit server (can self-host) | LLM plugins incl. Anthropic; MCP tools. Not Claude Code driving | Yes | Yes | Silero + own semantic turn-detector transformer | WebRTC only; a local mic needs a client app | Active, Apache-2.0. Server-oriented; heavy for a single-user Mac tool |
| mlx-audio (Python, plus mlx-audio-swift) | The model layer, not a framework: Kokoro, Qwen3-TTS, Whisper, Parakeet, Qwen3-ASR, Smart Turn, Silero, Sortformer; OpenAI-compatible REST server | None | Model-level streaming only | None | VAD and Smart Turn models in the Swift package | None | Active, MIT. Use as the model runtime |
| sherpa-onnx | ASR (streaming + offline), TTS, VAD, keyword spotting, speech enhancement; CPU or CoreML EP. Bindings: Python, Swift, Rust, Node, Go, C | None | Streaming ASR yes | None | Silero VAD | None | v2.0.2 (2026-11-19), very active, Apache-2.0. Ambient already uses Parakeet through ort |
| FastRTC (Gradio) | Bring your own STT/TTS | None | Callback style | Yes | Built in (Silero) | WebRTC/WebSocket + Gradio UI only | Maintained by Gradio/HF, MIT. Browser-centric |
| Vocode | Not checked in depth; appeared stagnant versus Pipecat | Anthropic via LiteLLM-style | Yes | Yes | Basic | Telephony-oriented | Treat as dead for a new project (not verified) |
| OpenAI Agents SDK `VoicePipeline` | None built in; STT/TTS are OpenAI models, though the workflow step is arbitrary code | Workflow is "your code", so it could call Claude, but no benefit | Streamed input with activity detection | Documented as an open gap in the pipeline path | Activity detection only | Examples use `sounddevice` | Fine library, wrong vendor; ignore |
| Apple native (AVAudioEngine, SpeechAnalyzer, AVSpeechSynthesizer) | Yes, fully on-device, ANE-backed | None (you write the glue) | Yes | You write it | AVAudioEngine voice processing gives AEC + AGC + noise suppression | Native audio I/O, best macOS device handling | System frameworks. SpeechAnalyzer quality not benchmarked here; AVSpeechSynthesizer voices are weaker than neural TTS |
| FluidAudio (Swift) | Parakeet TDT v3 (210x RTFx on M4 Pro), Parakeet EOU 120M streaming, Kokoro, PocketTTS (~80 ms first audio), Silero VAD, LocalVQE AEC (beta, 16 ms) on ANE | None | Yes | You write it | Silero + EOU | Native | Active, Apache/MIT. Strong Swift-native option |
| soniqo/speech-swift, argmax-oss-swift (WhisperKit, TTSKit) | MLX + CoreML ASR/TTS | None | Yes | You write it | Varies | Native | Active, community |
| Rust crates (cpal, ort, sherpa-onnx crate, whisper-rs, webrtc-audio-processing) | Yes via ort/sherpa-onnx; MLX only via FFI | None; Agent SDK is TS/Python, so Rust would shell out or speak MCP | You assemble | You write it | Silero via ort | cpal or Core Audio via objc2 (ambient does this) | Parts are mature, but there is no voice-agent framework |
| No framework, custom pipeline | Anything | Whatever you like, including the Agent SDK directly | You write it | You write it | Pick Silero + Smart Turn | Any | Cost: all glue and edge cases are yours |

Key framework findings

- Pipecat is the only framework that bundles all of: local MLX Whisper, Kokoro/Piper TTS, Silero VAD, Smart Turn v3, interruption handling, a local-audio transport and an Anthropic service. None of the frameworks can drive Claude Code itself; each calls a raw LLM. Driving Claude Code or the Agent SDK means a custom processor in Pipecat, or an MCP bridge (as ambient does).
- Pipecat `LocalAudioTransport` is PyAudio with no echo cancellation. Barge-in on laptop speakers will self-trigger unless the user wears headphones, the mic uses macOS voice processing, or a software AEC (LocalVQE, WebRTC AEC3) is added. A WebRTC browser transport gets browser AEC for free.
- Echo cancellation on macOS is the biggest practical problem. Apple's voice processing (AVAudioEngine `setVoiceProcessingEnabled`) is the only built-in AEC, and a third-party SDK's docs say it is unreliable on Mac speakers and recommend headphones or no interruption on built-in speakers (docs.thestage.ai, undated). Treat that as a claim to test, not a fact.
- Claude Code `/voice` (code.claude.com/docs/en/voice-dictation) covers push-to-talk dictation into the prompt with coding-tuned vocabulary. A new project adds value only through spoken replies, hands-free capture, or interruption.

## 2. Language trade-offs

| | Python | TypeScript | Swift | Rust |
|---|---|---|---|---|
| Mac ML models | Best: mlx-audio, mlx-whisper, Pipecat services, sherpa-onnx wheels | Weak: sherpa-onnx Node binding, otherwise cloud or sidecar | Good: FluidAudio (ANE), mlx-audio-swift, WhisperKit/TTSKit, speech-swift | OK via ort/sherpa-onnx; MLX only via FFI. Ambient measured CPU beats CoreML EP for its workload (ADR 0005) |
| Audio I/O and AEC | sounddevice/PyAudio, no AEC; process-level quirks | Poor natively | Best: AVAudioEngine voice processing, device routing, permissions | Core Audio via objc2 works (ambient), but no ready AEC beyond webrtc-audio-processing |
| Packaging | uv CLI or plugin is trivial; menu-bar app is awkward (needs py2app or a launcher; TCC mic permission attaches to the host process) | pnpm CLI trivial; menu-bar via Electron or a Swift shell | Native menu-bar app, signed, proper mic permission | Signed app possible (ambient does it) but UI needs objc2 or webview |
| Fit with Claude Agent SDK | Official Python SDK | Official TS SDK, closest to Claude Code itself | No official SDK; shell out to `claude -p` or use MCP | None; shell out or MCP |
| the user's conventions | uv, matches | pnpm, matches | Not in their stack but he already has a signed-app pipeline | His ambient language |
| Iteration speed | Fastest | Fast | Slower build/sign cycle | Slowest |

## 3. What is reusable from ambient (read only)

Facts from `ambient (github.com/jasonm4130-labs/ambient)` (Rust, `Cargo.toml` v0.0.3, MIT; ADR 0018 dated 2026-10-09):

- Ambient already has a voice reply path. `ambient talk` (`src/talk.rs`, 706 lines): push-to-talk audio is trimmed with VAD, transcribed with Parakeet on-device, sent as text to a target (an agent inbox script), the reply is awaited and spoken. SIGTERM silences the voice mid-word, which is its barge-in mechanism.
- `voice/` is a Python uv project (`ambient-voice`, Python 3.12) with optional engines: `mlx-audio==0.5.8` (Qwen3-TTS), `supertonic`, `kokoro-onnx`, and `sounddevice` for playback. It speaks over a JSON-lines stdin/stdout protocol with ready/speaking/done events (`src/assist/voice.rs`, 1060 lines). A cloned voice used about 1.1 GB. This helper is the most reusable piece, and it is already a separate process.
- ADR 0018: the agent's judgement runs in the user's Claude Code session; ambient serves MCP tools (`watch_meeting`, `wait_for_transcript`, `speak`, `stop_watching`). That is a precedent for "Claude Code drives, a tool speaks".
- Ambient's ASR is Parakeet TDT 0.6b (v2 fp16 and v3 int8) through `ort` 2.0.0-rc.13, CPU only (ADR 0005), plus Silero VAD, pyannote segmentation and WeSpeaker, with hand-written feature front ends (ADR 0006). Core Audio capture uses `objc2-core-audio` and a process tap (ADR 0001). None of that applies cleanly to a speaker-and-mic conversation; there is no AEC or voice-processing code in ambient (grep found no hits for voice processing).
- Reuse as a library is poor: it is a single crate with a binary, `ort` pinned to an rc, and models bundled in the repo. The brief says to keep the new project separate, so the reuse that makes sense is (a) copy the `ambient-voice` JSON-lines TTS protocol or depend on it as a sidecar, (b) reuse ADR learnings (CPU-only ASR, no CoreML EP), (c) reuse the Parakeet model files.

## 4. Recommended stack

Python (uv) with Pipecat, with the Claude Agent SDK as the brain, in a push-to-talk-first design:

- Pipecat pipeline: LocalAudioTransport (or a small custom sounddevice transport) to Silero VAD to Smart Turn v3 to `WhisperSTTServiceMLX` or a Parakeet service, to a custom `ClaudeCodeProcessor` that wraps the Python Claude Agent SDK session (streams text deltas), to Kokoro or mlx-audio TTS, to the speaker.
- Start in push-to-talk or headphones mode, so AEC is not blocking. Add voice processing or LocalVQE later for open-speaker barge-in.
- Rationale: Pipecat gives VAD, turn detection, interruption frames and swappable local/cloud STT and TTS today, for free; Python is where MLX models and the Agent SDK both live; uv matches the user's conventions; and it stays a separate project.
- Fallback: if the Pipecat custom-processor route fights the Agent SDK's streaming/permission model, drop to a no-framework Python loop (sounddevice, silero-vad, mlx-audio, Agent SDK) of roughly 300 lines. Pipecat's value is mostly turn-taking and interruption, which other teammates may find simpler to hand-roll.
- If a polished menu-bar app is wanted later, wrap the Python engine in a thin Swift shell (mic permission, hotkey, status item) rather than rewriting models. A pure Swift stack (FluidAudio + AVAudioEngine voice processing) is the strongest alternative if AEC proves decisive, but it has no Agent SDK, so it would talk to `claude -p` or an MCP server.

## 5. Biggest uncertainties

1. Echo cancellation and barge-in on Mac speakers: untested here; decides Pipecat-with-PyAudio versus a Swift front end.
2. Whether Pipecat's frame model composes cleanly with the Agent SDK (tool calls, permission prompts, multi-second tool runs with no audio). No existing Pipecat Claude Code integration was found.
3. Latency of Agent SDK turns (not benchmarked) versus the direct Messages API.
4. Vocode status, Apple SpeechAnalyzer quality and LocalVQE (beta) maturity were not verified in depth.

## Sources

- https://github.com/pipecat-ai/pipecat/releases/tag/v1.16.0 (2026-11-12)
- https://pypi.org/project/pipecat-ai/
- https://docs.pipecat.ai/api-reference/server/utilities/turn-detection/smart-turn-overview
- https://docs.pipecat.ai/api-reference/server/services/stt/whisper
- https://github.com/pipecat-ai/pipecat/blob/main/src/pipecat/transports/local/audio.py
- https://github.com/pipecat-ai/smart-turn
- https://docs.livekit.io/agents/ and https://github.com/livekit/agents
- https://github.com/Blaizzy/mlx-audio and https://github.com/Blaizzy/mlx-audio-swift
- https://pypi.org/project/sherpa-onnx/ (2.0.1, 2026-10-26) and https://github.com/k2-fsa/sherpa-onnx/releases (v2.0.2, 2026-11-19)
- https://github.com/gradio-app/fastrtc
- https://openai.github.io/openai-agents-python/voice/pipeline
- https://github.com/FluidInference/FluidAudio and https://docs.fluidinference.com/introduction
- https://github.com/soniqo/speech-swift and https://github.com/argmaxinc/argmax-oss-swift
- https://developer.apple.com/videos/play/wwdc2023/10235 (voice processing in AVAudioEngine)
- https://docs.thestage.ai/apple_sdk/docs/source/apple_sdk.audio_nodes.html (AEC on Mac speakers claim)
- https://code.claude.com/docs/en/voice-dictation
- ambient (github.com/jasonm4130-labs/ambient): AGENTS.md, README.md, Cargo.toml, src/talk.rs, voice/pyproject.toml, docs/adr/0005, 0006, 0018, docs/developing/live-assistant.md

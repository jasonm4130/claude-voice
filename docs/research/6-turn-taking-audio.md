# 6. Turn-taking and audio plumbing on macOS (research, 2026-11-22)

Nothing was installed or run; ambient was read only. "Vendor-run" = benchmark published by the vendor of one of the models compared.

## Headline

- Ambient already ships a push-to-talk "talk" path (`src/talk.rs`: app buffers a hold, pipes PCM to a child, Silero trim, Parakeet, reply spoken through a voice helper, SIGTERM = barge-in). It is the closest prior art; reuse it rather than start a VAD-driven loop.
- Recommend push-to-talk first (release = end of turn, no turn detector needed), optional hands-free later via Silero + Smart Turn v3.2 with a long coding-specific silence floor.
- Echo: use headphones/AirPods as the default, mute-while-speaking plus half-duplex on laptop speakers, and VoiceProcessingIO only as an opt-in. VPIO has real traps (below).

## 1. VAD and end-of-turn table

| Model | Type | Latency / runtime | Accuracy evidence | License | Notes for the user |
|---|---|---|---|---|---|
| Silero VAD v6 (v6.2.x) | frame VAD, ~2 MB, 512-sample (32 ms) frames at 16 kHz | <1 ms/chunk CPU; ONNX | Silero wiki (maintainer-run): multi-domain ROC-AUC 0.97 (v6), 0.96 (v5), 0.93 TEN, 0.73 WebRTC; ESC-50 noise-only accuracy 0.87 v6 vs 0.42 TEN | MIT | Already in ambient (`models/silero_vad.onnx`, 629 KB, via `ort`). Known weak spots: voice-like music, very high-pitched voices. Pip package pulls torch; ship the ONNX only. |
| TEN VAD | frame VAD, 10/16 ms hops, 16 kHz only | RTF 0.016 on M1 (README) | Claims better precision-recall and faster offsets than Silero (own plots, no numbers printed) | Apache-2.0 plus extra terms (no use competing with Agora; bars enabling third parties to build apps) | Faster offset detection is attractive for barge-in, but the license wording is non-standard. Not worth swapping for a 32 ms vs 10 ms gain. |
| Pipecat Smart Turn v3.2 | audio-only semantic EOT, Whisper-Tiny encoder + linear head, 8M params, 8 MB int8 ONNX | 12.6 ms on c7a.2xlarge, 59.8 ms c8g.medium (v3.0 blog); runs only after VAD sees silence; up to 8 s audio window | Own test set: 92.63% overall, English 94.26% (v3.2); v3.1 English 90.66% on the same set. LiveKit's independent-ish eot-bench ranks it 8th at 300 ms budget (46.9% false cut-offs, English) | BSD-2 (weights, data, training code) | Best open, local, permissive option. 23 languages. Pairs with Silero. v3.0 2025-09-11, v3.1 2025-12-03, v3.2 2026-01-07. |
| LiveKit Turn Detector v1.1-mini | audio-only EOT, local CPU | not published | eot-bench English: 25.6% false cut-offs at 300 ms; 1124 ms mean added latency at 5% false-cutoff budget (LiveKit-run) | LiveKit Model License; per one secondary source usable only with LiveKit Agents (verify before relying) | Better than Smart Turn on LiveKit's own benchmark, but license ties it to their stack. |
| LiveKit Turn Detector v1.1 (full) | audio + reads agent's last message | cloud (LiveKit Inference) | 13.2-13.4% at 300 ms; 810 ms at 5% cut-off budget (blog 2026-11-20, two days old) | hosted, billed past allowance | Not local-first. Useful as the "ceiling" reference. |
| Deepgram Flux | STT with built-in EOT, cloud | `eot_threshold` 0.5-1.0 (default 0.7), `eager_eot_threshold` 0.3-0.9, `eot_timeout_ms` 500-60000 (default 5000) | eot-bench: 22.3% at 300 ms, 1409 ms at 5% (LiveKit-run; older table showed 1151 ms) | commercial cloud | Eager EOT lets the LLM start early and cancel on `TurnResumed`. Cloud, so off-profile for local-first. `eot_threshold=1.0` + `ForceEndTurn` = bring your own turn detector. |
| AssemblyAI | STT with built-in EOT, cloud | not checked | eot-bench: 49.4% at 300 ms (LiveKit-run, older table); shows n/a on the 2026-11 leaderboard | commercial | Weak on that benchmark; not investigated further. |
| Kyutai semantic VAD | built into Kyutai streaming STT | not verified this session | not verified | not verified | Mentioned in the brief, but I did not fetch a primary source. Treat as unverified; the stt-models teammate may cover it. |
| WebRTC VAD | classic, 1/0 per frame | negligible | ROC-AUC 0.73 | BSD | Only as a cheap pre-gate. |

Benchmark caveat: eot-bench (LiveKit, code Apache-2.0, data CC-BY-4.0) replays real human-to-agent turns and sweeps threshold, minimum silence and timeout. Krisp publishes a benchmark where Krisp is first. None is independent. The measure that matters is "dead air after the user truly finished, at a fixed false-cutoff rate".

### How long to wait

Data points from eot-bench, English, mean dead air added at a 5% false-cutoff budget: best model about 0.8 s (v1.1, all sets), open local models 1.1-1.4 s, silence-only VAD about 1.6 s. At a 10% budget the best model needs about 0.4 s and local models 0.7-1.0 s. So even good detectors need roughly 0.8-1.4 s of dead air to keep false cut-offs near 5%. LiveKit's own short-turn set shows the worst case (1.1-1.6 s).

My inference for a coding agent (not from a source): people dictating code instructions pause to think, name symbols, and read file paths, so false cut-offs are costlier than slow replies, and acting on a half-sentence ("delete the...") is destructive. Suggested policy:

1. Smart Turn v3.2 gating a silence floor of about 1.0 s (end turn only if the model says complete) and a hard cap of about 2.5-3 s of silence.
2. Split the response into two stages. After about 0.6-0.8 s of silence, start transcription, planning and a short spoken acknowledgement; require the full EOT decision before any tool execution that writes or deletes. A `TurnResumed`-style cancel (Flux's pattern) makes speculative work safe.
3. In push-to-talk mode skip all of this: release is the end of turn.

## 2. Interaction mode recommendation

| Mode | Pros | Cons here |
|---|---|---|
| Push-to-talk (global hotkey, hold or toggle) | Deterministic turn boundary, no false triggers in a room with others, no echo problem while the key is down, nothing recorded when idle (privacy), simplest TCC story | Hands needed; but the user is at a keyboard when using Claude Code |
| Wake word | Hands-free | Extra failure mode (false accepts when others talk), needs always-on mic. openWakeWord: code Apache-2.0 but pretrained models CC BY-NC-SA (fine for personal use; custom training via Colab <1 h). Porcupine: custom words in seconds, ~97.3% at 1 false alarm / 10 h (Picovoice claim), free tier limited to ≤3 users and AccessKey required |
| Always listening + VAD + EOT | Most natural | Worst fit for shared rooms: picks up colleagues and TV, needs AEC and speaker diarisation to avoid answering the wrong person, highest privacy surface (ambient's own docs note VAD discarded a TV, but also would drop quiet real speech) |

Recommendation: ship push-to-talk (hold-to-talk, with tap-to-toggle for long dictation) as v1. Add an opt-in "hands-free" mode later as VAD + Smart Turn, enabled only on headphones, with a wake word or a "listening" toggle rather than permanent open mic. Ambient's own docs already refuse talk while a recording is running because the mic is shared, which suggests the same exclusivity rule.

## 3. Barge-in and interruption

Mechanics used by the main frameworks:
- OpenAI Realtime (WebSocket): on `input_audio_buffer.speech_started`, stop playback immediately, record milliseconds actually played, send `conversation.item.truncate` with `audio_end_ms`; server deletes the unheard transcript. Over WebRTC/SIP the server tracks this itself. Over-reporting `audio_end_ms` errors. (OpenAI docs; AIVAX post 2026-10-27 lists real client bugs in how this number is computed.)
- Pipecat: on interruption the pipeline cancels every processor; the assistant aggregator commits only text that was actually spoken, because TTS text frames are pushed in sync with audio playback.
- Twilio Conversation Relay: sends the exact text played before cutoff so the app can trim history.
- LiveKit Adaptive Interruption Handling (GA 2026-03-19, Agents Python 1.5.0+): an audio model separates real barge-in from backchannel ("mm-hmm"), coughs, typing. Claims 86% precision, 100% recall at 500 ms overlap, rejects 51% of VAD barge-ins, ≤30 ms inference, median 216 ms of audio to trigger. LiveKit-run, and it is a LiveKit Agents feature.

Design for the user's setup:
1. Play TTS from a queue keyed by sentence. Track a playback clock (frames actually written to the output device, minus device latency), not generation time.
2. On interrupt: stop output within one buffer, drop the queue, then rewrite the assistant message in the Claude Code conversation to the sentences fully or partially played (word timestamps from the TTS if available, else sentence granularity), with a marker such as "[interrupted by user]". Whatever Claude Code integration is chosen (cc-integration teammate) needs a way to feed back "what was heard"; with a hook/MCP design that is a message to the agent, not a context edit.
3. Barge-in trigger by mode: in push-to-talk, pressing the key is the interrupt (this is what ambient does: SIGTERM on re-press). In hands-free mode require Silero speech for about 200-300 ms while the AEC is active, and treat anything under about 0.4 s as backchannel (ambient already uses `MIN_SPEECH_S = 0.4` for slips of the key).
4. Do not let a barge-in cancel in-flight tool execution; interrupt speech, not work, unless the user says stop.

Ambient doc gap: `docs/developing/live-assistant.md` lists "No barge-in: the assistant finishes its sentence" as not in v1, so the talk path has barge-in only via key re-press.

## 4. Echo cancellation on macOS

Options:

| Approach | How well it works | Rust / Python / Swift | Costs |
|---|---|---|---|
| Headphones/AirPods (no AEC needed) | Best; removes the problem | any | AirPods drop to Bluetooth HFP (low-quality, around 16 kHz mono, SCO) the moment the mic is active; playback quality also falls, and the TTS sounds worse. Apple's `bluetoothHighQualityRecording` option exists in AVAudioSession but is not available in the EU and I could not confirm it applies to macOS. Workaround: use the MacBook's built-in mic with AirPods output (user-selected, or pin the input device by UID). |
| VoiceProcessingIO / AVAudioEngine `inputNode.setVoiceProcessingEnabled(true)` | Hardware-assisted AEC, AGC, noise suppression on Apple's own path; the best choice when it is wired correctly | Swift: easy. Rust: `objc2-core-audio` (already in ambient) or `objc2-avf-audio`, or `sys-voice` crate (MIT, Dec 2025, "likely to have bugs"). Python: via a Swift helper or PyObjC | Traps: (a) it ducks/pauses other audio (Spotify, music); macOS 14+ lets you set `voiceProcessingOtherAudioDuckingConfiguration` (min level), the sys-voice README claims it cannot be disabled, the Apple doc says you can reduce it; (b) it only cancels audio that your own process renders through the same unit/engine, so TTS must play through the same AVAudioEngine; screenpipe's issue #3938 (2026-06-09) measured 0 dB ERLE because the output element was disabled in their cpal fork; PR #7285 (2026-09-24) fixed it by pinning a cpal change; (c) it changes input gain and format (24 kHz mono seen in the AirPods case); (d) on AirPods during a Meet call, screenpipe's VPIO broke the shared input (issue #6213, 2026-08-13). |
| WebRTC AEC3 (via LiveKit `livekit-rs`/webrtc-audio-processing, or Pipecat with a WebRTC transport) | Good, cross-platform, you supply the far-end reference yourself so it works with any output path | Rust crates exist (`webrtc-audio-processing`); Python via LiveKit or aiortc; build/packaging effort | Needs accurate far-end alignment and delay estimate; more code than VPIO for a single-process app. Not verified on M-series this session. |
| speexdsp AEC | Dated, weaker on laptop speakers with nonlinear distortion | C library; Rust bindings exist | Not recommended in 2026. |
| Software gating (half-duplex: mute mic input while TTS plays, or lower VAD gain) | Robust but gives up barge-in by voice | trivial | Combine with PTT: key down = mic live, TTS ducked. |
| Transcript-level echo filter | Already in ambient's live assistant: drop a line if it overlaps the assistant's own speech in time (±3 s) and shares ≥60% of the words; short lines (<3 words) must be wholly inside | Rust | Last-resort safety net, not primary |

Recommended stack: PTT + half-duplex + headphone default; for speakers-and-hands-free, one process that owns both capture and TTS playback through an AVAudioEngine with voice processing on, with ducking configured to minimum, plus ambient's transcript echo filter as a backstop. Make the voice helper (currently Python `sounddevice` OutputStream in `voice/src/ambient_voice/player.py`) a separate process, which means the AEC reference never sees its audio, so VPIO would not cancel it. This is the main architectural reason to move playback into the same Swift/Rust process as capture if hands-free speakers are wanted.

### Mic permissions (TCC) for a CLI vs a signed app

- A bare CLI run from a terminal is attributed to the terminal app (the "responsible process"); the grant sits on Terminal/iTerm/Ghostty/the IDE and each terminal needs its own. Claude Code's own terminal counts as its own responsible process. If launched via `open` / LaunchServices from a bundle, TCC attributes it to the bundle.
- A signed .app with `NSMicrophoneUsageDescription`, and with the hardened runtime also the `com.apple.security.device.audio-input` entitlement, gets its own stable grant and a proper prompt. Ambient does exactly this (`Ambient.entitlements`, `make-app.sh`, stable signing identity via `setup-signing.sh`). Ambient's docs state the system-audio tap returns all-zero samples when the bare binary is run from a terminal.
- Practical consequence: keep the mic in a signed menu-bar app (like Ambient) and let the CLI/Claude Code side talk to it over a socket or the existing `ambient talk --pcm` pipe; do not capture from a hook script or MCP server subprocess spawned by Claude Code.

## 5. Reusable bits from ambient (github.com/jasonm4130-labs/ambient) (read only)

- `src/talk.rs` and `docs/using/commands.md#talk`: push-to-talk turn pipeline. App buffers a hold in memory, pipes raw f32 LE mono to `ambient talk --pcm`, child trims with VAD, transcribes with Parakeet, sends text through a `Target` (an agent inbox script today), polls for the reply (~1 s), speaks it holding `speaking.lock`, emits JSON events on stdout (`heard`, `nothing`, `queued`, `sent`, `reply`, `spoken`, `text_only`, `dry_run`, `no_reply`). `MIN_SPEECH_S = 0.4`. SIGTERM/`--stop` silences mid-word (barge-in on key re-press). Reply is markdown-stripped and cut to 600 chars. Refuses while a recording is running. The audio is never written to disk. A Claude Code `Target` would be the main new piece.
- `src/vad.rs`: Silero ONNX through `ort` (`=2.0.0-rc.13`, coreml feature), 512-sample frames, hysteresis ON 0.50 / OFF 0.35, MIN_SPEECH 250 ms, MIN_SILENCE 400 ms, 200 ms pad, relative level floor (+15 dB) to trim quiet edges. Documents that Silero reports 0.6-0.9 on quiet room noise, and that level separated real speech from an empty room by only 2 dB; so a VAD alone will not gate an open mic reliably. `Vad::turns` (no merging across silences) is the right entry point for turn splitting.
- `src/assist/` + `voice/` (Python, uv): TTS helper with six tones, `speaking.lock` coordination, designed voices; `docs/developing/live-assistant.md` echo filter rules and "no barge-in" limitation.
- Mic and system-audio capture in `src/session.rs`, `src/capture.rs` (Core Audio process taps via `objc2-core-audio`, lock-free ring written from the realtime IO block; mic has its own device and rate). `make-app.sh` bundle + Info.plist (`NSMicrophoneUsageDescription`, `NSAudioCaptureUsageDescription`) and minimal entitlements. These are the answer for permissions and signing.
- I did not find a global hotkey or CGEventTap implementation in ambient source from grep (`menubar.rs` has none). The talk.rs header says "the app holds the microphone and buffers a push-to-talk hold", but I could not locate the hold/hotkey code; it may live in the menubar app path I did not read in full. Check before assuming it exists.
- Taxonomy page (`the local repos/llm-wiki/pages/voice-agent-failure-taxonomy.md`): turn taking and barge-in is listed as failure #5 with no fix summarised; sources are publisher descriptions, not transcripts. Useful point: fixing sounds without timing does not hold, so evaluate end-of-turn and echo together.

## Biggest uncertainties

1. Whether VPIO works well with a TTS stream played by a separate process or a Python helper (my reading says no; unverified by experiment). A cheap test: a 50-line Swift AVAudioEngine program that plays a clip with voice processing on and records ERLE.
2. Real false-cutoff rates for the user's own dictation style (coding vocabulary, long thinking pauses); eot-bench data is customer-service-style and vendor-run.
3. Kyutai semantic VAD and AssemblyAI's turn model were not verified from primary sources.
4. Whether LiveKit's v1.1-mini license really restricts use outside LiveKit Agents (secondary source only).

## Sources

- Pipecat Smart Turn repo https://github.com/pipecat-ai/smart-turn ; v3 blog (2025-09-11) https://www.daily.co/blog/announcing-smart-turn-v3-with-cpu-inference-in-just-12ms ; v3.1 blog (2025-12-03) https://www.daily.co/blog/improved-accuracy-in-smart-turn-v3-1 ; v3.2 benchmark https://huggingface.co/pipecat-ai/smart-turn-v3/blob/main/benchmarks/smart-turn-v3.2-cpu.md ; model card https://huggingface.co/pipecat-ai/smart-turn-v3
- LiveKit eot-bench leaderboard https://livekit.com/benchmarks/eot-bench ; repo https://github.com/livekit/eot-bench ; Turn Detector v1.1 blog (2026-11-20) https://livekit.com/blog/turn-detector-v1-1 ; v1.0 blog (2026-06-17) https://livekit.com/blog/solving-end-of-turn-detection ; docs https://docs.livekit.io/agents/logic/turns/turn-detector/
- Secondary survey (license and benchmark summaries, treat as secondary) https://github.com/kadirnar/voice-agent-next/blob/main/docs/research/04-turn-taking-vad-interruptions.md ; Evalgent summary https://www.evalgent.com/blog/end-of-turn-detection-flux-silero-turn-detector
- Silero quality metrics https://github.com/snakers4/silero-vad/wiki/Quality-Metrics ; TEN VAD https://github.com/TEN-framework/ten-vad ; Cekura comparison (2026-10-26) https://www.cekura.ai/blogs/what-is-silero-vad
- Deepgram Flux config https://developers.deepgram.com/docs/flux/configuration ; eager EOT https://developers.deepgram.com/docs/flux/voice-agent-eager-eot
- Barge-in: OpenAI https://developers.openai.com/api/docs/guides/realtime-conversations ; https://developers.openai.com/api/reference/resources/realtime/client-events ; AIVAX post https://aivax.net/blog/openai-realtime-api-interruptions-conversation-item-truncate/ ; Pipecat https://docs.pipecat.ai/pipecat/fundamentals/interruptions ; Twilio https://www.twilio.com/en-us/blog/insights/ai-voice-agent-interruption-handling ; LiveKit adaptive interruption https://livekit.com/blog/adaptive-interruption-handling
- AEC: Apple WWDC23 "What's new in voice processing" https://developer.apple.com/videos/play/wwdc2023/10235 ; ducking config doc https://developer.apple.com/documentation/avfaudio/avaudioinputnode/voiceprocessingotheraudioduckingconfiguration ; sys-voice crate https://github.com/tigy32/sys-voice ; screenpipe VPIO issues https://github.com/screenpipe/screenpipe/issues/3938 , https://github.com/screenpipe/screenpipe/issues/6213 , https://github.com/screenpipe/screenpipe/pull/7285
- AirPods HFP: https://supermegaultragroovy.com/2021/01/28/more-on-avaudioengine-airpods ; Apple doc https://developer.apple.com/documentation/avfaudio/avaudiosession/categoryoptions-swift.struct/bluetoothhighqualityrecording
- TCC responsible process: https://github.com/shinyaoguri/metaphor/blob/main/docs/permissions.md ; https://github.com/ghostty-org/ghostty/issues/9263 ; Apple https://developer.apple.com/documentation/bundleresources/requesting-authorization-for-media-capture-on-macos
- Wake word: openWakeWord https://github.com/dscripka/openWakeWord ; Porcupine https://picovoice.ai/products/voice/wake-word ; comparison https://get.jinn.today/blog/jinn-wake-word-system
- Local: ambient (github.com/jasonm4130-labs/ambient) (src/talk.rs, src/vad.rs, src/capture.rs, docs/developing/live-assistant.md, docs/developing/vad-and-chunking.md, docs/adr/0004-vad-chunking.md, Ambient.entitlements, make-app.sh, voice/src/ambient_voice/player.py); the local repos/llm-wiki/pages/voice-agent-failure-taxonomy.md

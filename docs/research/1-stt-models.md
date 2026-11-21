# STT models for a "Claude talks to me" voice layer (research date 2026-11-22)

Target: the user, M5 Max 128 GB, local-first, talking to Claude Code (code identifiers, file names, CLI terms). No models were installed or run; everything below is from published sources. Each claim is tagged [indep] (third-party benchmark or repro), [vendor] (vendor or model-card claim), or [mixed].

## Findings that shape the choice

1. **Latency is a non-issue for batch-on-utterance local models on this machine.** Qwen3-ASR 0.6B 8-bit runs at 66x realtime, 1.7B 5-bit at 36x, Parakeet v3 INT8 at 117x on Apple Silicon (Soniqo benchmarks, undated page, read 2026-11-22) [indep-ish, vendor-run]. A 5 s utterance decodes in well under 0.2 s after the speaker stops. True streaming partials only buy live captions, not a faster reply.
2. **End-of-turn is the real latency lever, and almost no local model provides it.** Only Apple SpeechAnalyzer (own VAD, 1584 ms final), Parakeet EOU 120M (fires on most but not all samples, 2582 ms) and Kyutai stt-1b-en_fr (semantic VAD, only in the Rust server) have it. For everything else, pair with Silero VAD plus a silence timer, or push-to-talk. Cloud Deepgram Flux and AssemblyAI have it built in.
3. **Australian accent.** The only multi-model, per-accent table found is AppTek Call-Center Dialogues (Interspeech 2026, 2026-06-18) [indep]. WER on en-AU: Qwen3-ASR 1.7B 4.7, Parakeet v3 5.2, Qwen3-ASR 0.6B 5.3, Canary-Qwen 5.2, Kyutai 2.6B 5.9, Granite 6.4, Canary-1B 6.6, Whisper v3 8.1, Whisper v2 9.3. AU sits near the best accent, and Whisper is clearly worse than the newer models. A separate PAREDA paper (2026-05-18) found the Whisper API at 18.2% WER on en-AU against 3.9% en-US, on NLP-research talk. A Mozilla community post (2026-03-23) says Whisper skews US/UK. No accent data exists for the cloud vendors.
4. **Technical vocabulary.** No accuracy leaderboard covers it. Evidence found:
   - VoiceCodeBench (arXiv 2608.28916, 2026-09-12) [indep] scores exact recovery of flags, file paths, URLs and IDs. WER rank barely predicts it. Best streaming: OpenAI gpt-live-transcribe (CTEM 91.8, strict TSR 68.7), Cartesia Ink 2, Deepgram Nova-3 (88.9 / 61.7), ElevenLabs Scribe v2 Realtime (84.0 / 46.3, worst of the named streaming set). Best batch: ElevenLabs Scribe v2 (91.6), Deepgram Nova-3 (90.9). Whisper large-v3: 87.6 / 54.3. Local Qwen3/Parakeet/Nemotron were not in the quoted excerpt, so check the full table.
   - asr-lab (2026-07-27) [indep, tiny n=31]: Parakeet mishears "kubectl" as "QBTL" and "docker" as "Duck or"; whisper.cpp scored lower WER on dev commands (7.6% vs 13.9%).
   - aiche.app (2026-07-30) [indep, small]: local Whisper beat Parakeet on Python dictation (2.10% vs 4.82%) and Kubernetes (4.99% vs 6.10%).
   - Conclusion: nothing recovers `foo_bar.ts` or `--no-verify` reliably. Plan on a post-ASR correction step (LLM or Claude itself, given repo file list as context). This matches the wiki finding that no vendor guarantees supplied terms and boosting causes false positives.
5. **Claude Code already ships `/voice` dictation** (code.claude.com/docs/en/voice-dictation, read 2026-11-22). It is hold-to-record or tap-to-record, "tuned for coding vocabulary", and adds project name and git branch as hints. That is a baseline for input to compare against. The doc excerpt does not say where the transcription runs, so check before assuming it is local.

## Comparison table

WER columns are not comparable across rows unless the source matches. OAL = Hugging Face Open ASR Leaderboard English average (lower is better), values as of 2026-11-18 to 2026-11-21 [indep]. Latency figures are noted by source.

| Model | Where | Streaming | Latency | WER | Built-in end-of-turn | Apple Silicon runtime | Vocab biasing | AU accent | Price |
|---|---|---|---|---|---|---|---|---|---|
| **Qwen3-ASR 1.7B** | Local | Yes in model (offline 1.63/3.38 vs streaming 1.95/4.51 on LibriSpeech clean/other, HF card 2026-01-21 [vendor]); streaming backend documented as vLLM, MLX streaming unconfirmed | Batch 36x RT on MLX 5-bit | OAL 6.15 (#17); LibriSpeech 1.32-1.52 MLX [indep-ish] | No | MLX (mlx-audio), CoreML export exists (0.6B only, slower) | Context prompting in model card (unverified here) | **4.7 (best of tested)** [indep] | Free, Apache 2.0, 2.7 GB peak |
| **Qwen3-ASR 0.6B** | Local | As above | 66x RT; already tested by the user 2026-10-30 | OAL (en shortform) 6.42; AU 5.3 | No | MLX | as above | 5.3 | Free |
| **Nemotron 3.5 ASR Streaming 0.6B** | Local (CoreML via FluidAudio, ANE) | Yes, cache-aware RNN-T, no revisions | First partial 910 ms at 560 ms chunk, 380 ms median word delay at 160 ms chunk (M4 Max, mattt card 2026-10-16 [indep]); sttbench M5 Max 2026-08-25 [indep] | 1.77% on sttbench TTS corpus; OAL-style 9.75 [indep] | No (app decides) | CoreML + ANE, also mlx-audio-swift | None in FluidAudio | Not measured | Free, OpenMDW-1.1 |
| **Nemotron 3.5 Transcribe 30B-A4B** | Local GPU/vLLM | No (batch) | Wiki: p50 3.0 s | OAL 6.12-6.13; wiki: 2x AssemblyAI WER on clinical | No | Offline Metal 144-207x RT in transcribe.cpp [indep]; not worth it for this | none | n/a | Free |
| **Parakeet TDT v3 / v2 0.6B** | Local | Chunked "live mode" (v3: 729 ms median delay, results revise ~2 s) | 75-117x RT | OAL 6.95 / 6.91; Earnings-22 ~11.2 [indep] | No | FluidAudio CoreML, MLX | None | v3 5.2 [indep] | Free |
| **Parakeet Realtime EOU 120M** | Local | Yes | First partial 797 ms; EOU event 2582 ms | 6.0% sttbench TTS corpus [indep]; no punctuation or casing | **Yes** (unreliable: fires on most, not all) | FluidAudio CoreML | None | n/a | Free |
| **Apple SpeechAnalyzer / SpeechTranscriber (macOS 26)** | Local, OS | Yes, volatile + final results | First partial 1200 ms, final 1584 ms via own VAD (sttbench, M5 Max) [indep] | LibriSpeech clean 1.82 (ties Whisper v3); Earnings-22 12.03; FLEURS-en 8.8 [indep]; sttbench 5.61% | **Yes** (VAD finalisation) | Native, ANE, <5 MB download | `AnalysisContext.contextualStrings` (<=100 phrases; Apple docs describe it for DictationTranscriber); custom LM + pronunciations for DictationTranscriber via SFCustomLanguageModelData | Not measured | Free |
| **Whisper large-v3-turbo** (WhisperKit / whisper.cpp / MLX) | Local | No native (chunked) | 12x RT WhisperKit | OAL 7.64 [indep]; LibriSpeech 1.71-1.93 | No | CoreML, Metal | `initial_prompt` free text (terminal context, term list); works but can echo the prompt | **8.1 (v3), weak** [indep] | Free |
| **Voxtral Mini 4B Realtime (2602)** | Local (mlx-audio) | Yes | 480 ms delay default; 6/8-bit MLX: first text 1.8 s, final 0.3 s after speech ends; fp16 cannot keep up (0.47x RT on M5 Pro) [indep, community card] | 8.8% streamed (40 clips, French-heavy); OAL 8.44 | No | MLX, 6/8-bit only | None | n/a | Free, Apache 2.0 |
| **Kyutai STT 1b-en_fr / 2.6b-en** | Local | Yes, 0.5 s / 2.5 s delay | 2.6b = 2.5 s delay, too slow | OAL 6.40 (2.6b); AU 5.9 | **Semantic VAD, Rust server only; not in MLX** (kyutai.org, undated) | MLX port | None | 5.9 | Free |
| **Moonshine streaming tiny/small/medium** | Local | Claimed; card says shipped code path not fully incremental | 80 ms look-ahead; medium 87x RT on M4 Max | medium OAL 6.66 | No | transcribe.cpp (Metal/CPU); mlx-audio-swift offline only | None | n/a | Free, MIT |
| **Deepgram Flux (English)** | Cloud | Yes | ~260 ms EOT claimed [vendor]; AU data region exists | Pipecat semantic WER 1.32% for Nova-3 (Sept 2026) [indep]; VoiceCodeBench CTEM 88.9 | **Yes**: EndOfTurn, EagerEndOfTurn (can add 50-70% LLM calls), TurnResumed; eot_threshold 0.5-1.0 | n/a | Keyterms up to 500 tokens, extra cost; vendor admits false positives | Not measured | US$0.0065/min promo (was 0.0077) |
| **AssemblyAI Universal-3.6 Pro Realtime** (3.7 Realtime / Realtime-Agent now listed) | Cloud | Yes | ~150 ms P50 post-VAD [vendor]; Coval 107 ms to final [mixed] | Pipecat 1.12% (U3.5 Pro) [indep-ish]; OAL 6.21 (batch U3.5 Pro, #18) | Yes: "reads as complete" model, 640-2560 ms max silence | n/a | Keyterms up to 100, included | Not measured | US$0.45/h (3.7 Realtime US$0.30/h); billed on session time incl. idle |
| **ElevenLabs Scribe v2 Realtime** | Cloud | Yes | ~150 ms [vendor] | Pipecat 3.05%; OAL batch Scribe v2 5.93; VoiceCodeBench streaming TSR 46.3 (weak) | Not documented in sources read | n/a | 50 keyterms (+US$0.08/h) | Not measured | US$0.22-0.39/h (sources disagree) |
| **OpenAI gpt-live-transcribe / gpt-realtime-whisper** | Cloud | Yes, five delay settings | No figure | VoiceCodeBench streaming: best CTEM 91.8, TSR 68.7, WER 5.9 [indep] | Realtime API has VAD (semantic VAD in older docs; not re-verified) | n/a | prompt, keywords | Not measured | US$0.017/min (US$1.02/h) |
| **Speechmatics Linden 1** | Cloud | Yes | <350 ms mean finalisation, ~440 ms P95 [vendor] | n/a | Yes: StartOfTurn/EndOfTurn | n/a | Custom dictionary up to 1,000 | AU region available | US$0.30/h |
| **Soniox stt-rt-v5 / Cartesia Ink 2** | Cloud | Yes | n/a | Ink 2 VoiceCodeBench CTEM 90.1 | n/a | n/a | n/a | n/a | ~US$0.12/h / US$0.39/h |

Leaderboard context (2026-11-21): top entries are mostly closed or unreleased (Zoom Scribe v2.1 Pro 4.87, Otter 5.21, Azure 5.50, ElevenLabs Scribe v2 5.93). Best open weights that run on a Mac: Cohere Transcribe 5.42 (Apache 2.0, 2B, gated), Qwen3-ASR 1.7B 6.15, Granite Speech, Parakeet 6.9. Differences under about 0.5 WER on the OAL average are noise for this use case.

## Ranked top 3 for this use case

1. **Qwen3-ASR 1.7B (or 0.6B) on MLX, run per utterance behind Silero VAD (or push-to-talk).** Best measured Australian-accent WER of anything compared, Apache 2.0, already proven on the user's machine, and at 30-66x realtime the decode adds under 0.2 s; end-of-turn comes from VAD plus a short silence timer, with LLM-side post-correction for identifiers.
2. **Nemotron 3.5 ASR Streaming 0.6B via FluidAudio (CoreML, ANE).** Genuine streaming with non-revising words at ~370 ms delay and near-zero GPU load, so live partials can show while the user speaks; weaker on the OAL average (9.75) and no vocab biasing, so use it for the live display and let #1 re-decode the finished utterance (the "dual-layer" pattern aiche.app recommends).
3. **Deepgram Flux (cloud) as the opt-in fallback.** The only option with tuned built-in end-of-turn plus eager-EOT for starting the LLM early, an Australian data region, and Nova-3 scores well on exact-token recovery; use it only if VAD-based endpointing feels sluggish or cuts the user off, since it sends audio off the machine.

Apple SpeechAnalyzer is the zero-dependency baseline (built-in VAD finalisation, <5 MB, ties Whisper on clean audio) but is slower to first partial (1.2 s) and mid-pack out of domain; worth one test run, not a primary pick. Whisper is not recommended as primary: no streaming, weakest AU number, though its free-text prompt is the easiest way to inject context.

## Open questions worth a quick local experiment

1. **Identifier recall on the user's own voice.** Record about 40 prompts with real repo content (file names, flags, snake_case, git commands) in an Australian accent; score exact-token recovery (VoiceCodeBench-style CTEM) for Qwen3-ASR 0.6B/1.7B, Nemotron streaming, Apple SpeechAnalyzer and Whisper turbo with a terminal-context prompt. The tts-asr-round-trip-check wiki page may help generate this cheaply, but TTS audio is not an accent test.
2. **Does Qwen3-ASR accept a text context prompt in mlx-audio 0.6.1?** If so, test biasing with the repo file list and watch for false positives.
3. **Is Qwen3-ASR streaming mode usable on MLX**, or only offline? Check the mlx-audio source before relying on partials.
4. **Endpointing.** Compare Silero VAD plus 600-900 ms silence against Apple's VAD and the Parakeet EOU model on conversational speech with mid-sentence pauses; also test a "keep talking" cue so Claude's TTS stops (barge-in).
5. **Claude Code's built-in `/voice`**: where does it transcribe, and how does its identifier accuracy compare to the local stack? It may make the input half unnecessary.
6. **Cohere Transcribe (OAL 5.42, Apache 2.0, 2B)** is the best open model I found but is gated and its Mac runtime is unverified; check for an MLX or CoreML port.

## Caveats

- Most per-vendor latency numbers are vendor claims; the independent latency data is the sttbench harness (M5 Max, TTS audio, not human speech) and the mattt Nemotron card (M4 Max).
- sttbench WERs use synthetic TTS audio, so the 1.77% for Nemotron is optimistic.
- Pricing pages disagree between aggregators (ElevenLabs realtime US$0.22 vs 0.39/h; Deepgram promo vs regular), and AssemblyAI's own pricing page now lists a 3.7 generation; verify before committing.
- Some pages (Dexto, Micdrop, Evalgent, AssemblyAI blog) are vendor-adjacent marketing; treat their rankings as weak evidence.

## Sources

- Open ASR Leaderboard mirrors: https://awesomepapers.io/speech-audio/leaderboards/Open%20ASR%20Leaderboard%20(English)/open-asr-english ; https://models.fru.dev/boards/open-asr ; https://paperswithcode.co/benchmark/open-asr-leaderboard ; https://raw.githubusercontent.com/huggingface/open_asr_leaderboard/main/scripts/data/en_shortform.csv
- Accent benchmark: https://www.isca-archive.org/interspeech_2026/beck26_interspeech.pdf ; https://arxiv.org/html/2605.17860 ; https://community.mozilladatacollective.com/why-whisper-still-struggles-with-australian-english-and-what-we-did-about-it
- Technical vocab: https://arxiv.org/html/2608.28916 ; https://github.com/openbenchmarks-labs/voice-code-bench ; https://github.com/Muzaffar-codes07/asr-lab ; https://aiche.app/blog/stt-model-comparison-2026
- Apple Silicon: https://github.com/jswent/sttbench ; https://soniqo.audio/benchmarks ; https://github.com/verliapp/stt-benchmark ; https://whispernotes.app/blog/apple-speech-vs-whisper ; https://huggingface.co/mattt/nemotron-3.5-asr-streaming-0.6b-coreml ; https://github.com/FluidInference/FluidAudio ; https://github.com/anomalyco/hex/blob/dev/docs/research/model-watch.md ; https://github.com/T0mSIlver/localvoxtral/issues/907
- Apple docs: https://developer.apple.com/documentation/speech/analysiscontext/contextualstrings ; https://developer.apple.com/documentation/speech/recognizing-speech-in-live-audio ; https://developer.apple.com/videos/play/wwdc2025/277
- Models: https://huggingface.co/Qwen/Qwen3-ASR-1.7B ; https://huggingface.co/flo5k5/Voxtral-Mini-4B-Realtime-2602-MLX-8bit ; https://kyutai.org/next/stt ; https://github.com/kyutai-labs/delayed-streams-modeling
- Cloud pricing and features: https://deepgram.com/pricing ; https://www.assemblyai.com/pricing ; https://elevenlabs.io/pricing/api ; https://dexto.ai/blog/best-speech-to-text-apis-for-voice-agents/ ; https://nextlevel.ai/blog/deepgram-vs-assemblyai-vs-speechmatics/ ; https://micdrop.dev/blog/top-speech-to-text-apis-voice-agents ; https://www.evalgent.com/blog/stt-providers-for-voice-agents ; https://www.assemblyai.com/blog/best-api-models-for-real-time-speech-recognition-and-transcription
- Open model rundowns: https://thinkscribe.ai/en/blog/open-speech-recognition-models-2026 ; https://pinggy.io/blog/best_open_source_self_hosted_speech_to_text_models/
- Claude Code dictation: https://code.claude.com/docs/en/voice-dictation
- Wiki: the local repos/llm-wiki/pages/asr-term-biasing.md, nemotron-transcribe.md

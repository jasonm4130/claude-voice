# TTS models for a "Claude talks to me" layer (as of 2026-11-22)

Research snapshot, November 2026. Figures are from the cited sources unless marked as measured; nothing here was benchmarked by this project.

Scope: text-to-speech for Claude Code replies on an Apple Silicon Mac, favouring local models. Nothing was installed or run; every number is from a web page read 2026-11-22. "Vendor" = the maker's own claim. "Indep." = Coval, Cekura, Artificial Analysis (AA) or a third-party blog.

## Bottom line

1. Local pick: **Qwen3-TTS (Apache 2.0)**. Runs on Apple Silicon via MLX, has streaming and incremental-text-input paths there, and can clone a voice or design one from a text description (for example an Australian voice). It needs a text-normalisation pre-pass and an ASR round trip, because all-caps acronyms are misread (one reported case: "TACO" read as "Takeo").
2. Local second: **Phonon 31M (Gradium, Apache 2.0, Oct 2026)**. A 64 MB model that starts speaking in about 5-9 ms on Apple CPU (vendor). It is the latency floor for a local layer. Quality is below Qwen3-TTS and the voices are fixed.
3. Cloud pick: **Inworld Realtime TTS-2 Flash**. Lowest independent first-audio, best independent score on numbers, codes and shorthand (about 93%), a WebSocket that takes LLM text as it is written, en-AU voices, $15 per 1M characters. Runner-up on naturalness: **ElevenLabs v4 Turbo**.

Biggest uncertainty: no one has measured end-to-end time to first audio on a current Apple Silicon Mac for LLM-token-streamed input into Qwen3-TTS or Phonon. Published local numbers are M1/M3/M4 laptops, different harnesses, and one is a vendor claim.

## Comparison table

TTFA = time to first audio. "Stream-in" = accepts incrementally arriving text (what an LLM emits).

| Model | Where | TTFA (source) | Stream-in | Naturalness | Tech text | Clone | AU English | Apple Silicon | License | Price |
|---|---|---|---|---|---|---|---|---|---|---|
| Qwen3-TTS 0.6B/1.7B (Alibaba) | Local | Vendor: "97 ms" (datacentre). M4, native MLX (mlx-node): 113 ms to first PCM, est. 565-640 ms presented with a 1 s prebuffer, RTF 0.54. mlx-audio `stream=True` was "effectively offline" (4.3 s first yield, M1 Max, 0.6B) in an April 2026 third-party repro. | Yes in mlx-node (sentence/phrase commit). mlx-audio: whole-string. | No open-weight AA score found. Cloud sibling Qwen-Audio-3.1-TTS-Plus is #3-4 on AA (1298-1300). | Known weak: all-caps acronyms (TACO, Takeo). | Yes, about 3 s of audio (Base). VoiceDesign from text description. | No preset. Clone a consenting AU speaker or VoiceDesign (untested). | MLX via mlx-audio and mlx-node. GGUF/llama.cpp too. | Apache 2.0 | Free |
| Phonon 31M / 40M (Gradium, Oct 2026) | Local | Vendor: 5-9 ms on MacBook Air M5 CPU, 26-47x real time. Under 20 ms on Apple devices. iPhone Neural Engine 9-12 ms. | Streams frame by frame (80 ms). Text-in granularity not documented. | AA open-weights Elo 1108 (below Fish/Breeze/Ming). Vendor listening test: 2098 vs Kokoro 2043. | Vendor: 1.5% WER on a hard set of numbers, dates, codes vs Kokoro 3.5%. Unverified. | Not in open weights. | No (fixed voices, e.g. Easton). 31M is English only. | CPU + Accelerate/KleidiAI, Core ML on iPhone. In Ollama (macOS first, 2026-10-24). | 31M Apache 2.0. 40M models CC BY-NC. | Free |
| Kokoro-82M | Local | CPU 1 core M5 Air: 776 ms (PyTorch, whole-sentence, via Gradium). About 300 ms on RTX 4060 Ti. | No (sentence at a time). | About 4.5 MOS (April 2026 blog). Phonon beat it in vendor test. | Needs numbers written out. No text normaliser. | No | No: US and UK only. | MLX (mlx-audio), Core ML (Sandbook moved to it Nov 2026). | Apache 2.0 | Free |
| ZONOS3-Mini (Zyphra, 2026-11-09) | Local | Vendor: under 150 ms on M3 MacBook Air; 80 ms on H100. | Unknown | Not on AA. Brand new. | Unknown | Yes, up to 60 s clip, no transcript. | Via clone | MLX, ggml, WebGPU | Apache 2.0 | Free |
| Kyutai TTS 1.6B (en/fr) | Local | No Mac figure found. Server: 75x real time per compute unit (vendor). | Yes, built for it (delayed streams; audio starts after the first words). | Not on AA | Unknown | Via voice embeddings repo, limited | No | PyTorch, Rust, MLX backends. | Weights CC-BY 4.0 | Free |
| Pocket TTS (Kyutai, Jan 2026) | Local | About 200 ms (vendor), CPU | Yes | Small-model class | Unknown | Yes (cloning repo gated) | No | CPU, M4 Air about 6x real time | Code MIT, weights CC-BY 4.0 | Free |
| VoxCPM2 (2B, Apr 2026) | Local | RTF about 0.3 on RTX 4090 (vendor) | Not shown | 48 kHz, "quality pick" per one blog | Unknown | Yes + voice design | Via design | GGUF/ONNX ports; NVIDIA-first | Apache 2.0 | Free |
| Chatterbox (Resemble) | Local | Not measured | Not shown | Good | Weak without normalising | Yes, MIT | Via clone | MPS, mlx-audio | MIT | Free. Maintainer retired it Aug 2026, no fixes. |
| Orpheus 3B / Dia2 / Sesame CSM | Local | Orpheus about 200 ms (vendor, GPU) | Orpheus: yes | MOS 4.6-4.7 (2025 numbers) | Unknown | Yes | No | mlx-audio supports CSM, Dia | Apache 2.0 (Orpheus has Llama terms) | No updates since late 2025 per one source. Dia2 card says research use. Treat as stale. |
| Fish Audio Drama 3 | Local (server GPU) | 89 ms on H200 (vendor) | n/a | Best open on AA: 1277 | Cekura S2.1-Pro 92% hard parts | Yes | Via clone | No: 35B params, server GPU | Free commercial under USD 500k revenue | $15/1M via API |
| Voxtral TTS 4B (Mistral) | Local (heavy) | Not found | Chunked | AA open 1094 | Unknown | Not in open release | Unknown | mlx-audio supports | CC BY-NC | $16/1M |
| Apple AVSpeechSynthesizer, Siri/Premium voices, Personal Voice | Local | Not researched. Background knowledge: effectively instant, on-device. | Per utterance | Below the neural models above | Not researched | Personal Voice = own voice only | Yes: en-AU system voices (Karen, Lee). Not verified this session. | Native | System | Free |
| Inworld Realtime TTS-2 Flash | Cloud | 45 ms median streaming (Cekura). 81 ms avg (Coval, us-east-1, to 2026-10-28). 0.17 s p50 phone-line test (Stork). Add network from AU. | Yes: WebSocket, many contexts per connection. | AA 1269 (TTS-2). Flash UTMOS-estimated 4.46. | 93.2% hard parts (Cekura). 27/27 numbers/email/address (Stork). Server-side normalisation for a subset of languages. | Yes, from 3 s. Same price as stock voices. | Yes: en-AU locale plus voices Banjo, Callum, Cooper, Hamish. | n/a | Proprietary | $15/1M chars (TTS-2 Flash), $25/1M (TTS-2) |
| ElevenLabs v4 Turbo / Flash v2.5 | Cloud | v4 Turbo: 69 ms (Cekura) / 194 ms (Coval avg). Flash v2.5: 75-100 ms vendor, 177-182 ms Cekura. | Yes, WebSocket. | AA #1-2: v4 1340, v4 Turbo 1339 | v4 Turbo 79.9%, Flash 64.4% hard parts (Cekura, rival's benchmark site). ElevenLabs docs: Flash reads "$1,000,000" wrongly; normalise text. | Yes (best-in-class tools) | Yes, community library (Clara, Lee, Amelia) | n/a | Proprietary | $40/1M (Turbo, Flash), $80/1M (v4) |
| Cartesia Sonic 3.6 | Cloud | 0.21 s first audio p50 (Stork). 286 ms (Cekura). Vendor 40-90 ms. | Yes | AA 1294 | 74.9% hard parts (Cekura) | Yes (Pro plan) | Yes: 14 AU voices (Ella, Arlo, Bronte, Fraser, Cooper, Jasper) | n/a | Proprietary | About $39-65/1M by plan |
| Gradium TTS | Cloud | 53 ms p50 (Coval, read 2026-11-19). 74 ms on AA. | Yes, WebSocket built for LLM tokens. | TTS Arena prelim #1 (1605). No AA Elo found. | Vendor claim: acronyms, emails, phone numbers correct. Cekura 79.5% hard parts. | Yes, 10 s | "Regional variants" in 5 languages. AU not confirmed. | n/a | Proprietary | Free 45k credits/mo, then from $12-13/mo (1 credit = 1 char) |
| Google Gemini 3.8 Flash TTS / Chirp 3 HD | Cloud | Not published | Limited | AA 1282 | Unknown | Gated | Yes: 30 en-AU Chirp voices | n/a | Proprietary | $16.49/1M (Flash TTS), about $30/1M (Chirp 3 HD) |
| Azure Neural HD, Amazon Polly | Cloud | Not published | Yes | Lower than leaders | SSML | Gated | Yes: Azure 19 en-AU, Polly Olivia/Russell/Nicole. Australian data-residency option. | n/a | Proprietary | $4-48/1M |
| OpenAI gpt-4o-mini-tts | Cloud | 300-600 ms | Weak | Mid | Unknown | No | No | n/a | Proprietary | **Retires 2027-01-06.** Replacement is Realtime API (gpt-realtime-2.1-mini), not a drop-in. Skip. |
| Hume Octave 2, Rime Mist v3, Deepgram Aura-2 | Cloud | Rime 0.24 s p50 (Stork); Aura-2 126-299 ms | Yes | Hume strongest emotion (vendor) | Rime 27/27 (Stork) | Hume yes | Rime: one AU voice (marlu). Deepgram: Hyperion, Theia. | n/a | Proprietary | $30-150/1M |

## Reading the evidence

- **Naturalness**: AA Speech Arena (blind votes, read 2026-11-22): Eleven v4 / v4 Turbo 1340, StepAudio 3 1307, Qwen-Audio-3.1-TTS-Plus 1298, Sonic 3.6 1294, Simba 3.5 1293, Gemini 3.8 Flash 1282, Fish Drama 3 1277. The top 2 are separated from the rest. Gaps under about 30 Elo are ties. TTS Arena V2 ranks differently (MiniMax Speech-02-HD, Gradium, Inworld 1.5 MAX on top), so no single leaderboard decides it.
- **Open-weights gap**: the best open model on AA (Drama 3) needs a 35B server GPU. Models that run on a laptop (Phonon 1108, Voxtral 1094, Fish S2 Pro 1101) sit about 200 Elo below the cloud leaders. Qwen3-TTS 0.6B/1.7B and Kokoro are not on the AA open board. "Local sounds as good as cloud" is not supported by any source I found.
- **Latency**: all cloud numbers exclude the network trip from the listener (a Coval figure is from AWS us-east-1; a VerticalAI guide says vendor 75-100 ms figures are measured at the vendor's servers). From Australia, expect cloud first audio to be vendor figure plus roughly 150-250 ms RTT (my estimate, not measured). A local model with 100-300 ms TTFA competes with cloud on real distance. The 300-550 ms voice-reply budget used here is for the whole turn (ASR end to first audio), so TTS should take under about 150 ms of it.
- **Technical text** (Cekura "hard parts" = numbers, codes, abbreviations; scored by transcription, so acronyms said as words are excluded): Inworld 93%, ElevenLabs v4 94% / Turbo 80%, Fish S2.1-Pro 92%, Cartesia 75%, Gradium 80%. None of these tests file paths, camelCase identifiers or `snake_case`. Every source says normalise before TTS.
- **Text normalisation** is the cheapest big win. EmergentTTS-Eval (NeurIPS 2025) found a GPT-4.1-mini normaliser lifted win rate from 51.7% to 76.7% on hard pronunciation, while a rule-based normaliser (WeText) made it worse (50.1%). Inworld and ElevenLabs both publish an LLM prompt for "speakable output". `speechready` (GitHub, 2026-10-27) cleans markdown/code fences/URLs and chunks streaming token feeds for TTS. Not tried.
- **Australian English**: no local open model ships an AU preset (Kokoro is US/UK only; Phonon 31M is English with fixed voices). Real AU options: Cartesia (14 voices), Inworld (en-AU locale and named AU voices), Google (30 Chirp voices), Azure (19), Polly, ElevenLabs library. Locally, clone or VoiceDesign via Qwen3-TTS.

## Ranked top 3

1. **Qwen3-TTS, local, via the native MLX path** (mlx-node or a patched mlx-audio). Reasons: the only local model here with documented MLX streaming, incremental text input, cloning and voice-design together; Apache 2.0; 2.2 GB RSS. Risks: mlx-audio's own streaming may still be fake; acronym misreads; AU accent unproven; M4 RTF 0.54 is fine but the 1 s playback prebuffer pushes presented latency to 0.6 s.
2. **Inworld Realtime TTS-2 Flash, cloud.** Best fit for an LLM-token stream of technical prose. Use it when local quality is not enough or for a fast fallback. Risk: vendor-heavy evidence (Cekura numbers and the Inworld site quote each other, Coval and Stork are independent), data leaves the machine, AU round trip unmeasured.
3. **Phonon 31M, local, as the low-latency fast path.** Use it for short acknowledgements ("on it", "done, tests pass") where 10 ms start beats voice quality, or as a stand-in while Qwen3-TTS spins up its first segment. Risk: vendor-only latency and accuracy; no AU voice; quality is mid.

Cloud naturalness pick if cost is no object: ElevenLabs v4 Turbo ($40/1M). Its hard-parts score is the weaker one, so pair it with an LLM normaliser.

## Experiments worth running (all cheap, on an Apple Silicon Mac)

1. **Time-to-first-audio on the target Mac**: feed the same 3 reply lengths token-by-token (simulated 60 tok/s) into (a) mlx-audio 0.6.1 `stream=True` Qwen3-TTS 1.7B 8-bit, (b) mlx-node `synthesizeStream` incremental input, (c) Phonon 31M via `uvx ptts`, (d) Kokoro via mlx-audio. Record text-submit to first audible sample with a loopback capture, not the first yielded chunk. Settles whether mlx-audio's streaming is real, and what the 1 s prebuffer costs.
2. **Acronym and technical-text battery** with an ASR round trip: 40 lines of real Claude Code output (paths, `snake_case`, `camelCase`, versions, hashes, PR numbers, TACO-style caps, ISO dates, `~/src`). Run raw vs after an LLM "speakable text" pass (Haiku-class, with the Inworld/ElevenLabs prompt as the base). Score WER and per-category failures for Qwen3-TTS, Phonon, Kokoro, Inworld Flash.
3. **AU voice**: Qwen3-TTS VoiceDesign ("Australian male, relaxed, Australia") and a Base clone from a short consented sample. Compare against Inworld Banjo/Callum and Cartesia Arlo/Ella. Judge by ear, then ASR-check.
4. **Sentence-chunking policy**: how many tokens or which punctuation to wait for before sending to TTS. This sets perceived latency more than the model choice. Compare commit-on-sentence vs commit-on-clause (mlx-node default 256 graphemes; Gradium's multi-turn pattern reuses one WebSocket).
5. **Cloud RTT check**: from your own region (for example Australia), measure first audio for Inworld, ElevenLabs Flash/Turbo, Cartesia, Gradium over WebSocket, p50 and p95 over 30 runs. Vendor figures will not hold.
6. **Optional**: ZONOS3-Mini on MLX (new, 2026-11-09, vendor under 150 ms on M3 Air) and Kyutai TTS 1.6B MLX backend as true text-streaming local alternatives.

## Gaps, flagged

- Apple AVSpeechSynthesizer, Personal Voice and macOS 26 Siri voices: not researched this session, row is background knowledge. Worth a 10-minute check as a zero-dependency fallback and a latency baseline.
- Qwen3-TTS technical-text accuracy has no independent figure beyond one reported TACO/Takeo misread.
- `Qwen-Audio-3.1-TTS-Plus` (cloud) ranks #3-4 on AA but is a different product from the open Qwen3-TTS weights. Do not read the cloud score as the local model's quality.
- Several roundup blogs (vdf.ai, webdiga, micdrop, builderai) are secondary and sometimes contradict each other on licences (Chatterbox retired Aug 2026 per vdf.ai). Check model cards before adopting.
- The Cekura benchmark covers its own sponsor-adjacent vendors (Inworld leads its own hard-parts table); Stork and Coval corroborate Inworld's latency but not its accuracy lead.

## Sources

- AA TTS leaderboards: https://artificialanalysis.ai/text-to-speech/arena?tab=leaderboard , .../leaderboard/provider-voice , .../provider-voice/open-weights , .../controlled-voice
- Aggregated AA + TTS Arena V2 (2026-11-18): https://17nas.com/tts-leaderboard.php
- Qwen3-TTS: https://qwen.ai/blog?id=qwen3tts-0115 , https://github.com/QwenLM/Qwen3-TTS
- mlx-audio streaming and cloning guides: https://blaizzy.github.io/mlx-audio/guides/streaming , https://blaizzy.github.io/mlx-audio/guides/voice-cloning , https://blaizzy.github.io/mlx-audio/models/tts
- Fake-streaming finding and fix (M1 Max, 0.6B): https://github.com/akaiHuang/mlx-qwen3-tts-real-streaming
- mlx-node native Qwen3-TTS streaming, M4 measurements 2026-10-08: https://github.com/mlx-node/mlx-node/blob/main/docs/tts.md
- Qwen3-TTS CUDA streaming server (A10G, 187 ms): https://callumjmac.github.io/posts/qwen-tts-streaming
- Phonon: http://gradium.ai/blog/release-phonon-open-weight , https://huggingface.co/gradium/phonon-31m-en , https://github.com/gradium-ai/xn-ptts
- Gradium API and pricing: http://gradium.ai/api , https://gradium.ai/pricing , https://gradium.ai/content/how-to-stream-tts-audio-real-time-bidirectional-streaming
- Local roundup (2026-11-14): https://vdf.ai/blog/best-local-tts-models ; others: https://webdiga.com/local-text-to-speech-models/ , https://micdrop.dev/blog/top-open-source-text-to-speech-models , https://www.cekura.ai/blogs/open-source-tts
- Kyutai: https://kyutai.org/tts , https://huggingface.co/kyutai/tts-1.6b-en_fr , https://github.com/kyutai-labs/pocket-tts , https://kyutai.org/blog/2026-10-20-pocket-tts-small/
- Dia2: https://github.com/nari-labs/dia2 ; Orpheus: https://github.com/canopyai/Orpheus-TTS ; VibeVoice: https://github.com/microsoft/VibeVoice
- Kokoro on Apple (Core ML move): https://sandbook.app/blog/kokoro-82m-apple-mlx-iphone
- Cloud latency/price: https://haass.io/blog/best-tts-api-2026 , https://www.stork.ai/blog/text-to-speech-api-phone-calls-test-2026 , https://www.evalgent.com/blog/tts-providers-for-voice-agents , https://limithit.com/voice , https://inworld.ai/tts-api , https://inworld.ai/tts , https://elevenlabs.io/pricing/api , https://elevenlabs.io/docs/eleven-api/guides/how-to/best-practices/latency-optimization
- Cekura TTS benchmark: https://benchmarks.cekura.ai/text-to-speech , https://github.com/cekura-ai/cekura-bench/blob/main/tts-bench/README.md
- Text normalisation: https://elevenlabs.io/docs/best-practices/prompting/normalization , https://docs.inworld.ai/tts/best-practices/prompting-for-tts , https://proceedings.neurips.cc/paper_files/paper/2025/file/04970a25af46918606ba2cf0a3d7905d-Paper-Datasets_and_Benchmarks_Track.pdf , https://github.com/berkerbatur/speechready , https://voxeval.com/blog/streaming-tts-text-normalization/
- Australian voices: https://www.cartesia.ai/voices/australian-accent , https://docs.inworld.ai/tts/capabilities/multilingual , https://inworld.ai/voices , https://verticalai.com.au/guides/voice-ai-providers-australia , https://www.murmurtts.com/blog/australian-accent-text-to-speech
- OpenAI TTS retirement: https://developers.openai.com/api/docs/guides/text-to-speech , https://community.openai.com/t/tts-shutdown-email-tts-1-gpt-4o-mini-tts-jan-6-2027-isnt-on-the-deprecations-page/1402731

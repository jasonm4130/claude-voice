# Speech-to-speech and full-duplex: skip or augment the cascade?

Researched 2026-11-22 via Parallel search (snippets only; nothing installed, nothing run). Claims are dated; figures are vendor-reported unless stated. Anything marked UNVERIFIED I could not confirm.

## Recommendation

**Cascade now, with a hybrid "front layer" built at the pipeline level (local ack/filler + barge-in), not a speech-to-speech front model. Run a time-boxed experiment with NemotronLabs VoiceChat 11B (MLX) as a local full-duplex front that delegates to Claude Code via a tool.**

Why:
1. Claude cannot be the speech model. As of Nov 2026 the Messages API has text and image input only; no audio content block, no speech endpoint (platform.claude.com API overview; SDK issue #1198 "audio input" closed not-planned 2026-08-06, "under consideration internally"). Claude app voice mode and Claude Code `/voice` are Anthropic's own voice offerings; `/voice` is dictation only, streams audio to Anthropic servers, needs a claude.ai login, and does not work over SSH. Claude Code and Cowork get dictation, not voice mode (Claude Help Center). So any "Claude talks to me" for Claude Code is text-in/text-out Claude plus someone else's ears and mouth.
2. The latency that matters is Claude Code's (tool use, seconds to minutes), not the 200 to 500 ms an s2s model saves. S2S wins on turn-taking feel, backchannels, barge-in; those can be approximated in a cascade with streaming STT, semantic VAD and cached acknowledgements.
3. S2S front models are the right shape only for the "speak while the agent works" gap. That exact pattern is now productised by OpenAI (GPT-Live-1 delegating to Codex), which validates it, but the productised version is cloud-only and fronts a non-Claude model.
4. Fidelity risk: a front model re-narrates Claude's result. Its own 9B brain can paraphrase wrongly, and tool-call provenance is murky (see wiki page voice-agent-latency-architecture: "sleight of hand" background tool call). For a coding agent, the spoken summary must be Claude's words, not the front model's.

## Model table

| Model | Type | Local on M5 Max 128 GB? | Latency (reported) | Cost | Tool calling / delegation | Brain quality | Licence |
|---|---|---|---|---|---|---|---|
| Kyutai Moshi (7B) | Full-duplex s2s | Yes, `moshi_mlx` 4/8-bit/bf16 (Kyutai repo) | 160 ms theoretical, ~200 ms on L4 | free | None. No tool channel | Poor. 4.3% on Big Bench Audio (llmconfigurator 2026-10-25, secondary source) | Code MIT/Apache, weights CC-BY 4.0 |
| Kyutai Unmute | Cascade wrapper (Kyutai STT + any LLM + Kyutai TTS) | Reference stack is Linux/CUDA, 16 GB VRAM, x86_64 only. Kyutai STT/TTS models ship MLX. Community `unmute-mlx-bridge` (2026-07-26, pre-1.0) runs the servers on Mac: TTS q8 1.84x real time, time-to-first-audio 1.05 to 1.54 s; 4-bit corrupts the TTS | "Below a second" (Kyutai); ~450 ms TTS multi-GPU, ~750 ms single L40S; STT delay 500 ms, "flush trick" cuts to ~125 ms | free | Any text LLM, so Claude works; function-calling demos ("bye" hangs up) | Whatever LLM you plug in | MIT code; models CC-BY 4.0 |
| NVIDIA PersonaPlex 7B (2026-01-15) | Full-duplex s2s, Moshi fine-tune | Yes via MLX ports (soniqo: RTF ~1.4 on M2 Max 8-bit, i.e. slower than real time there; ~11 GB RAM; M5 Max unmeasured) | 170 ms smooth turn, 240 ms interruption (model card, FullDuplexBench) | free | None native. Persona via text role prompt | Moshi-class; English only | MIT code, NVIDIA Open Model License weights |
| NVIDIA NemotronLabs VoiceChat 11B (arXiv 2609.21967, Oct 2026) | Full-duplex s2s with function-call output stream | Yes. MLX builds: soniqo RTF 0.92 to 0.94 on M5 Pro, ~8.7 GB peak; community 3-bit GPTQ build RTF 1.04 on base M5 (fanless) | ~450 ms turn-taking; 118 ms p95 per 160 ms chunk on H100 | free | Native tool calling on a separate channel; soniqo shows a recorded session calling an MCP tool (Apple Reminders) locally | Nemotron Nano 9B v2 backbone; 38.8% Big Bench Audio (secondary source) | OpenMDW 1.1 |
| MiniCPM-o 4.5 (OpenBMB, 2026-02-03) | Full-duplex omni, 9B (Qwen3-8B core) | Yes via llama.cpp-omni; full duplex needs M4 Max/24 GB+ | not stated in snippets | free | Not confirmed (UNVERIFIED) | Mid | Apache-2.0 code |
| Qwen3-Omni 30B-A3B (2025-09) / Qwen3.5-Omni (2026-03-30) | Omni, turn-based | ~79 GB bf16 fits in 128 GB; MLX status UNVERIFIED | 234 ms audio first packet theoretical (GPU, 1 concurrent), 211 ms per Qwen blog | free | Function calling supported (Qwen blog; Qwen3.5-Omni adds search + function calling) | Strongest open option | Apache-2.0 |
| Ultravox v0.7 (2025-12) | Audio-in LLM (speech understanding), no speech out | Weights open (MIT) on GLM 4.6 355B; not practical locally | Hosted | Hosted pricing UNVERIFIED | Yes | Good | MIT weights |
| Sesame CSM-1B | TTS only (conversational speech model) | Yes | n/a | free | n/a. Not s2s; the demo model was not released | n/a | Apache-2.0 |
| Step-Audio | Not researched successfully | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED |
| Dessa (Block) | Announced full-duplex s2s, "runs on M4 Max+" | Waitlist only as of 2026-10-25, no weights | n/a | n/a | n/a | n/a | n/a |
| OpenAI gpt-realtime-2.1 / mini | Cloud s2s | No | Realtime first audio 0.39 s mean over WebRTC (Stream benchmark, published 2025-10-06, likely older model) | Audio $32 in / $64 out per 1M tokens; mini $10 / $20 (OpenAI pricing page) | Function calling and remote MCP | Strong | Proprietary |
| OpenAI GPT-Live-1 (2026-09-10) | Cloud full-duplex front model, designed to delegate | No | not stated | $0.05 per minute for the voice layer, backend billed separately | Two delegation modes: Responses (OpenAI model) or client delegation (your app runs any agent harness and returns results). OpenAI's own example connects it to the Codex SDK | Front model only | Proprietary |
| Gemini 3.8 Live | Cloud native-audio s2s | No | Stream benchmark: Gemini Live first audio 3.06 s vs OpenAI 0.39 s (older model, WebSocket vs WebRTC, treat as stale) | $3 in / $12 out per 1M audio tokens (~$0.005 / $0.018 per min) | Async function calling, NON_BLOCKING by default in 3.8; 3.1 Flash Live is sync only | Strong | Proprietary |
| Amazon Nova 2 Sonic | Cloud s2s on Bedrock | No | not stated | UNVERIFIED | Async tool calling out of the box; 8-minute connection limit | Moderate | Proprietary |

Full-Duplex-Bench-v3 (arXiv 2604.04847, 2026-04-06) benchmarks tool use for full-duplex agents; the snippet rows (Gemini Live 3.1, Grok, Ultravox, "Cascaded") lost their column headers, so I do not quote them. One readable signal: the cascaded system scored 100.0% on one column but had the slowest value (10.12 s) in another, which fits "cascades are accurate but slow to act". UNVERIFIED mapping; read the paper before relying on it.

## Architectural patterns compared

| Pattern | Latency to first sound | Claude is the brain? | Local on M5 Max | Cost | Tool/delegation | Main risk |
|---|---|---|---|---|---|---|
| A. Pure cascade (streaming STT, Claude via Agent SDK/CLI, streaming TTS) | ~0.7 to 1.2 s to first audio, plus Claude's own TTFT; long silence during tool work unless filled | Yes, fully; speaks Claude's exact words | Yes (STT/TTS local; Claude is cloud either way) | Claude usage only | Native: it is Claude Code | Dead air during tool runs; weaker barge-in; needs echo handling |
| B. Unmute-style wrapper (Kyutai STT + semantic VAD + any LLM + Kyutai TTS) | "Below a second" (Kyutai) | Yes | Partly: stock stack is CUDA/Linux only; community MLX bridge is pre-1.0, TTS RTF only ~1.8x on Mac | Free | Via the LLM | It is a cascade with better turn-taking; same dead-air problem; Mac port maturity |
| C. Hybrid: S2S front model that chats/acks/handles barge-in and delegates to Claude Code as a tool | Front responds in ~200 to 450 ms regardless of Claude's speed | Claude does the work; front model does the talking and summarising | Yes with VoiceChat 11B (RTF ~0.92 on M5 Pro) or MiniCPM-o; cloud with GPT-Live-1/Gemini Live | Local free; GPT-Live-1 $0.05/min + backend | Yes, via function channel / client delegation. Gemini and Nova run tools async so the front keeps talking | Front paraphrases Claude's output; 9B brain can misroute; double prompt-injection surface; echo cancellation; provenance |
| D. Pure S2S (front model is the brain) | Lowest | No. Claude is replaced, so no repo-aware agent | Possible | n/a | Weak | Fails the requirement |

## Findings that drive the decision

- Anthropic has no speech API. Claude app voice mode (beta, all plans; 2026-07-23 update: Opus/Sonnet/Haiku, connected tools, many languages; "Claude Fable is not currently available in voice mode") runs on Anthropic's own stack and is not exposed as an API. Claude Code's `/voice` is hold-to-talk dictation (STT only). Neither gives Claude a voice for Claude Code sessions.
- The delegation pattern is real and productised: OpenAI describes GPT-Live-1 as "can delegate reasoning and tool calls to a backend text model … or a third-party model"; "client delegation" lets your app run "any model, agent harness, or service" and send results back; "backend work can continue when the caller interrupts the assistant; your application decides whether to finish or cancel it". That maps onto Claude Code driven through the Agent SDK. Cost: audio and session context go to OpenAI; GPT-Live-1 does not accept Chat Completions or Realtime endpoints (separate `v1/live/sessions`).
- Gemini 3.8 Live and Nova 2 Sonic both do async tool calls natively (conversation continues while tools run). Gemini 3.1 Flash Live does not. This is the capability a front model must have for Claude Code (tool runs of tens of seconds).
- Open full-duplex models with tool calling now exist and run on Apple Silicon: NemotronLabs VoiceChat 11B is the first open full-duplex model with a function-call stream (NVIDIA, 2026-10-01). Measured by third parties on M5-class Macs at RTF ~0.92 to 1.04, 7.5 to 9 GB. Those are single-stream, hot-compute numbers; soniqo explicitly says they do not capture learned turn-taking latency.
- Older Moshi-family models (Moshi, PersonaPlex) have no tool channel and weak reasoning; they are conversation-feel research, not a front for an agent.
- Unmute does not get you away from the cascade; it is a well-tuned one. Its useful ideas to copy: semantic VAD (end-of-turn without cutting you off) and the STT "flush trick" (~500 ms to ~125 ms).

## Suggested path for the user's use case

1. Build the cascade (teammates' angle). Claude Code stays the brain; speech is a thin layer on top.
2. Add the cheap parts of the hybrid inside the cascade: immediate local acknowledgement ("on it"), spoken progress lines driven by tool-use events, barge-in that cancels TTS and interrupts the Claude turn. This captures most of the front-model benefit with no second brain.
3. Experiment, one afternoon: VoiceChat 11B MLX as the front with one tool `ask_claude_code(task)` and a rule that Claude's reply is read back verbatim or via TTS bypass (not paraphrased). Measure: echo/barge-in on laptop speakers, misrouted tool calls, whether it speaks over Claude's result.
4. Do not pick cloud GPT-Live-1/Gemini Live unless local-first is relaxed; they are the best-polished version of C, but you would be sending voice to OpenAI/Google and fronting Claude with another vendor's model.

## Biggest uncertainty

Whether a local 9B full-duplex front (VoiceChat 11B) delegates reliably and stays out of Claude's way on an M5 Max; all numbers above are third-party, single-stream, hot-compute, and none test delegation to a coding agent. Second: Step-Audio and Nova 2 Sonic pricing were not verified.

## Sources

- Kyutai Unmute: https://github.com/kyutai-labs/unmute ; https://kyutai.org/unmute ; https://kyutai.org/next/stt
- Kyutai Moshi + MLX: https://github.com/Kyutai-labs/moshi ; https://github.com/kyutai-labs/moshi/blob/main/moshi_mlx/README.md ; https://github.com/kyutai-labs/delayed-streams-modeling
- Unmute on Mac (community, pre-1.0, 2026-07-26): https://github.com/nwalker85/unmute-mlx-bridge
- NVIDIA PersonaPlex: https://research.nvidia.com/labs/adlr/personaplex ; https://huggingface.co/nvidia/personaplex-7b-v1
- NemotronLabs VoiceChat: https://arxiv.org/html/2609.21967 ; https://huggingface.co/nvidia/NVIDIA-NemotronLabs-VoiceChat-11B ; https://huggingface.co/roman220220/NemotronLabs-VoiceChat-11B-gptq-mlx-mixed
- Local Mac measurements: https://soniqo.audio/voice-agents
- Local voice roundups (secondary): https://www.collegica.org/ai/voice-agents (2026-09-13) ; https://www.dograh.com/hub/blogs/open-source-speech-to-speech-models (2026-11-10) ; https://llmconfigurator.com/en/blog/local-voice-models-2026 (2026-10-25)
- MiniCPM-o 4.5: https://huggingface.co/openbmb/MiniCPM-o-4_5 ; https://openbmb.cn/en/blog/minicpm-o-4-5-technical-report
- Qwen3-Omni: https://arxiv.org/html/2509.17765v1 ; https://github.com/QwenLM/Qwen3-Omni ; https://qwen.ai/blog?id=fdfbaf2907a36b7659a470c77fb135e381302028
- Sesame CSM: https://github.com/SesameAILabs/csm ; https://huggingface.co/sesame/csm-1b
- Ultravox v0.7: https://www.ultravox.ai/blog/introducing-ultravox-v0-7-the-world-s-smartest-speech-understanding-model
- OpenAI GPT-Live-1: https://openai.com/index/introducing-gpt-live-1-in-the-api ; https://developers.openai.com/api/docs/guides/live ; https://developers.openai.com/api/docs/guides/live-delegation ; https://developers.openai.com/api/docs/models/gpt-live-1
- OpenAI pricing and Realtime: https://developers.openai.com/api/docs/pricing ; https://developers.openai.com/api/docs/guides/realtime-conversations
- Gemini Live: https://ai.google.dev/gemini-api/docs/live-api/capabilities ; https://ai.google.dev/gemini-api/docs/live-api/tools ; https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/live-api/asynchronous-function-calling ; https://aistudio.google.com/docs/pricing
- Realtime vs Gemini latency (stale, 2025-10-06): https://getstream.io/blog/speech-apis
- Amazon Nova 2 Sonic: https://docs.aws.amazon.com/nova/latest/nova2-userguide/sonic-async-tools.html ; https://docs.aws.amazon.com/nova/latest/nova2-userguide/sonic-tool-configuration.html ; https://aws.amazon.com/blogs/aws/introducing-amazon-nova-2-sonic-next-generation-speech-to-speech-model-for-conversational-ai
- Full-Duplex-Bench-v3: https://arxiv.org/html/2604.04847
- Anthropic: https://support.claude.com/en/articles/11101966-using-voice-mode-on-claude ; https://claude.com/blog/think-through-hard-problems-in-voice-mode (2026-07-23) ; https://code.claude.com/docs/en/voice-dictation ; https://platform.claude.com/docs/en/api/overview ; https://github.com/anthropics/anthropic-sdk-python/issues/1198 ; https://platform.claude.com/docs/en/cli-sdks-libraries/libraries/openai-sdk
- Wiki: the local repos/llm-wiki/pages/voice-agent-latency-architecture.md ; voice-agent-failure-taxonomy.md

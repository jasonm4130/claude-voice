# Local full-duplex front for "Claude talks to me": November 2026 sweep

Researched 2026-11-22. Read-only: model cards, READMEs, changelogs, GitHub issues, one NVIDIA source file, HF API listings, `gh` stats. Nothing downloaded, installed or run. Tags: **[vendor]** = the model's own authors; **[indep]** = a third party measured it; **[unverified]** = I could not trace it to a primary page; **[inference]** = my reading of code or architecture, not a claim anyone made. Builds on `5-speech-to-speech.md`; it does not repeat the cloud options.

## Headline

**No local full-duplex model on a Mac has a documented, supported way to speak given text verbatim as of 2026-11-22.** Two have the mechanism inside their own code and need a patch: NemotronLabs VoiceChat (NVIDIA's CUDA reference wrapper already forces pre-tokenised text into the agent's text channel, which its TTS then speaks; the Mac ports were not checked and soniqo's has no scripted speech) and Sophon-Realtime's Mac engine (the talker reads the thinker's text word for word). On a Mac the same gap covers interim acks and progress lines, not just the final summary. So the recommended design is a **split front**: a local full-duplex model handles conversation, acks, backchannels and barge-in, and Claude's ~35-word summary is spoken by a deterministic path, either a forced-text patch into the front's own voice or a separate local TTS fed into the same echo-cancellation reference.

Corrections to the leads in the brief:
- **Sophon on Mac cannot delegate yet.** The Mac README says "Camera input, tool calls and zero-shot voice cloning are not in the Mac version yet". Live mode needs the CUDA engine's tool bridge on `PORT+700`. Live mode also speaks results "in its own words", so it is not verbatim even on CUDA (sophon-realtime `mac/README.md`, `live/README.md`, read 2026-11-22). The Mac 4B latency of 0.3 to 0.5 s was measured on an **M4 Max with MLX memory capped at 10.5 GB and simulated audio**, with no live microphone [vendor].
- **VoiceChat on Mac does not keep talking while a tool runs.** Soniqo's runtime "freezes the shared language and EAR-TTS timeline while the external result is pending", the default tool timeout is 15 s, at most five tools are allowed, and the frame p95 is 76 to 78 ms against an 80 ms deadline on an M5 Pro [indep, soniqo docs 2026-11-20].
- **Duopra is Linux/CUDA only.** The weights are gated, the runtime is verified only on an A800, and the repo asserts no blanket licence.
- **Haru-4B's "~65 ms" appears on no page I opened** [unverified]. Haru-4B is a pretrained base model, "does not follow instructions the way an assistant does", and has no tools.
- HF `lastModified` shows the MLX VoiceChat builds existed by **2026-08-05 to 08-08** (mlx-community) and 2026-09-28/29 (roman220220), so not October. These are last-modified dates, not release dates.

## Candidate table

Grading of the "speak given text" column: **Documented** = a supported API; **Patch** = the mechanism exists in the project's own code and needs exposing; **No** = no path without retraining or an external TTS.

| Model | Params / Mac memory | Licence | Apple Silicon runtime (who measured, chip) | Response latency / RTF | AEC + barge-in on laptop speakers | Tools / delegation (async?) | Speak given text | Voice cloning | Benchmarks | Maturity (2026-11-22) |
|---|---|---|---|---|---|---|---|---|---|---|
| **NVIDIA NemotronLabs VoiceChat 11B** (existed by early Aug 2026; card last modified 2026-09-22; arXiv 2609.21967 v1 2026-09-18) | 11B hybrid Mamba/Transformer (Nemotron Nano v2 9B + FastConformer + separate EAR-TTS + codec). INT5 ~8.7 GB peak RSS; 23.67 GB peak physical footprint in a 63 s profile | OpenMDW-1.1 weights (permissive, commercial OK); speech-swift Apache-2.0 | **Real.** soniqo speech-swift (Swift/MLX), Homebrew CLI; mlx-audio Python port (`mlx-community/...-4bit`). Soniqo measured on an **M5 Pro 48 GB** [indep of NVIDIA, but vendor of the runtime]; community 3-bit build RTF 1.04 on base M5 [unverified, from prior report]. Not measured on an M5 Max | Turn-taking ~450 ms; FDB v1 smooth turn 448 ms, interruption 480 ms [vendor]. Mac: RTF 0.92 to 0.94, first playable audio 74 to 76 ms hot compute [soniqo]. Post-tool speech 3.56 to 4.00 s after end of input with a 200 ms mock provider [soniqo] | Soniqo CLI keeps capture and playback on one AVAudioEngine "for Apple AEC"; RNN-T barge-in [soniqo docs]. No speaker-vs-headset test published | **Native function channel**, MCP via `--mcp-config`, max 5 tools, 15 s default timeout. **Not async on Mac:** speech frozen while the result is pending. NVIDIA's wrapper has an "FC Async" path that kills the tool thread on barge-in (`rnnt_fc_interrupt_ms`, 240 ms) | **Patch, CUDA evidence only.** NVIDIA's Python `nemotron_voicechat_inference_wrapper.py` writes a pre-tokenised redirect message into `gen_text` frame by frame (`_redirect_tokens_queue`, l.3033 to 3044) and feeds `acknowledgement_tokens` straight to EAR-TTS during tool waits (l.1480 to 1490). Per-tool "on-hold" messages are documented for NVIDIA's container [vendor]. **The Mac ports are unchecked:** code search found no such hook in speech-swift or mlx-audio [unverified], and soniqo says its runtime has "no ... scripted assistant speech" | 37-frame speaker prompt in speech-swift [soniqo]; cloning not documented, so no Australian voice [unverified] | AU-Harness BFCL avg 56.1%; FDB v3 Pass@1 33%, tool selection 82.5%, args 42.2% [vendor]; VoiceBench #2 open FD [vendor] | NeMo/Speech 18.8k★ (pushed 11-21); speech-swift 1.3k★, 14 issues, pushed 11-18; mlx-audio (now Neywa-Labs) 8.3k★ |
| **Sophon-Realtime Mac** (repo created 2026-11-04; v1.5.0 2026-11-18) | 32B Flash-4bit MLX (~24 GB download, ~26 GB while talking), or 4B Flash MLX 8-bit (9.2 GB, ~11 GB) | Apache-2.0 code and weights. **Open issue #3:** thinker derives from DuplexJev-32B-Para (CC BY-NC 4.0); vendor says Apache applies and offers commercial agreements. Personal use fine | **Real but young.** Own MLX engine (`mac/engine.py`, `aec.py`, `serve.py`). All numbers on an **M4 Max 36 GB, simulated real-time input, no live mic** [vendor]. Issue #1 was opened by an M5 Max 128 GB user; no report posted | 32B: speaks 0.9 to 1.1 s after you stop, up to ~2.5 s when unsure; stops ~0.15 s after barge-in. 4B: 0.3 to 0.5 s [vendor] | **WebRTC AEC3 built in**, "speakers are fine"; barge-in and back-channel resume [vendor]. `--no-aec` for headsets | **None on Mac today.** Live mode (GPT-Live `session.delegation.created` / `commentary.append`) is CUDA only. Community fork `Mearman/sophon-realtime` has branches `feat/mac-tool-calling`, `feat/mac-live-gateway`; the fork author reports well-formed calls on an **M3 Max** [fork author, issue #5]; maintainer accepted the plan 2026-11-14. On CUDA, Live mode is async ("keeps talking") | **Patch [inference].** The talker reads the thinker's tagged text and, since 2026-11-13, "waits for the next word"; ASR-checked word for word [vendor]. Pushing Claude's text into that queue is a Python edit. Issue #15 (2026-11-21) asks for a `say` event; no answer yet. The CUDA-only E2E build has `/tts` | Tag/Flash/E2E on CUDA; **not on Mac** (built-in voices only, no Australian) | **CUDA server builds, not the Mac engine:** FDB v1 avg 94.0 (32B), 87.7 (4B Flash); FDB v3 Pass@1 48% (best of several runs); VoiceBench 82.8 (32B), 62.4 (4B); Big Bench Audio 81.8% (32B), 44.3% (4B) [vendor]. **Mac engine** (4-bit thinker, different turn question): only Smart Turn v3.2 samples, 91.7 / 92.7% en / zh (32B) and 90.0 / 89.7% (4B) [vendor] | 511★, 12 open issues, pushed 11-20, 107 commits in 2.5 weeks |
| **Duopra** (HF 2026-11-12; arXiv 2611.25773) | 9.4B (Realtime-Venus-Audio = MiniCPM-o 4.5 arch, Qwen3-8B thinker) | Weights MIT (card), base Apache-2.0; app repo: "no blanket open-source licence"; gated download | **No Mac path.** Linux x86_64 + CUDA 12.8, verified on an A800. MiniCPM-o 4.5 itself runs duplex on Mac via llama.cpp-omni (M4 Max RTF < 1) and vllm-metal (2026-11), but Duopra's runtime is not ported [inference] | Factual-answer latency 10.42 s including tool execution [vendor] | Not documented | **Best fit to the design:** silent action channel every 1 s; backend is one more tool `query(task)`; results injected asynchronously at the next 1 s boundary while it keeps talking [vendor] | **No [inference].** The talker is conditioned on thinker hidden states; the lineage drops the end of replies (llama.cpp-omni issue #134: 0.85 of text spoken; Python reference 0.95) [indep] | Not documented | FDB v3 Pass@1 49.3% (DeepSeek backend), 47.7% direct; FDB v1 interruption 91.3%; VoiceBench 55.9; English WER 7.66% [vendor] | 18★, 0 issues, pushed 11-20 |
| **Haru-4B** (2026-11-12) | 5B (Qwen3.5-4B backbone, VibeVoice codec), 7.5 Hz frames | Apache-2.0 | `haru-speech-mlx` 0.1.0 (2026-11-13), native macOS app; 16 GB practical minimum [vendor] | 133 ms frame; "~65 ms" [unverified] | Recommends wired headphones; no AEC documented | **None.** Base model, character card only | No (text and audio summed into one position) | Yes, from a reference clip | None published | 716★, 4 commits |
| **MiniCPM-o 4.5** (2026-02-03) | 9B; GGUF set ~8.3 GB, ~10 GB runtime | Apache-2.0 | llama.cpp-omni on Metal: TTFT < 650 ms, Token2Wav RTF 0.47 on **M4 Max** [vendor]; duplex needs M4 Pro 36 GB+ [vendor]; vllm-metal duplex 2026-11 [vendor] | as left | Not documented | None native; fine-tune Realtime-Venus adds in-stream `<delegate>` with async results (CUDA harness) | No; TTS drops reply tails (issue #134) [indep] | Yes (ref audio) | FDB v1 used as a reference system by SGLang-Omni | MiniCPM-V repo 27k★ |
| **LFM3-Audio-2B / LFM3-Omni-2B** (Liquid, Sept to Nov 2026) | 2B; 2.7 GB 8-bit MLX | LFM Open License v1.0 | Official MLX builds; mlx-audio STS support | Turn-based. Community duplex LoRA (MAdel121): 59 ms per 80 ms step on MPS, **~1.2 s** turn pickup, ~3 min session cap, headphones required, **non-commercial** [LoRA author's own figures] | No AEC (headphones) | Not documented | **Documented TTS mode** ("Perform TTS ...") but not inside a duplex session | Fixed voices | FDB v1 (LoRA): pause TOR 0.044, backchannel TOR 0.000 [author] | Research prototype |
| **Kyutai Moshi / PersonaPlex 7B** | 7B; PersonaPlex 8-bit ~11 GB | Moshi CC-BY 4.0; PersonaPlex NVIDIA OML | moshi_mlx; speech-swift PersonaPlex RTF ~1.4 on M2 Max [indep] | FDB v1 reply 0.07 to 0.27 s but talks over most pauses | No | None | No (text stream is the model's own inner monologue) | 18 presets | FDB v1 (Kyutai re-run): PersonaPlex smooth turn 95.8% | Moshi last push 2026-09-09; Kyutai has released no new duplex model since [indep, fullduplex.ai] |
| **Qwen3.5-Omni** (2026-03) | Flash/Plus sizes; open weights for 3-Omni 30B-A3B | Apache-2.0 | No MLX speech-output path found [unverified] | 235 ms first packet on GPU (theoretical) [vendor] | n/a | Function calling, turn-based | n/a | n/a | n/a | QwenLM/Qwen3-Omni last push 2026-04-23 |
| Others swept | MOSS-Live (hosted API, free beta, no open weights found [unverified]; FDB v3 51%); Shizuku-Duplex (Japanese, background model, hosted); Saturn-Duplex-5B-DE (Haru fine-tune, German, CC BY-NC-ND); Raon-SpeechChat-9B (CC BY-NC, Docker demo); caramel-1 (413M, trained only on speech, no text); Duo-1.0 (inclusionAI world model, MiniMax H3 licence, HF created 2026-11-12); Trelis duplex-0 (201M research checkpoint); AwakenFullDuplex-Qwen3Omni (30B, FDB v1 0.44 s turn latency) | | | | | | | | | |

## How each would wire to Claude Code

Common backend for all of them: a small local service wraps the Claude Agent SDK (`query()` with streaming, `interrupt()`, and a `canUseTool` callback). It exposes three things to the front: `ask_claude_code(task)`, which **returns immediately** with a ticket ("started, task 7"); `status(task)`; and a push channel that delivers progress lines and the final ~35-word spoken summary. **The front never gets an approve tool.** Permission prompts go to a deterministic path: the screen, a key, or an exact spoken phrase matched in the ASR transcript by code, never a model-generated tool call.

**VoiceChat 11B (speech-swift CLI or mlx-audio).**
- Delegation: `--mcp-config` pointing at a local stdio MCP server exposing `ask_claude_code` and `status`, as read-only tools. Soniqo's default `--mcp-write-policy` is **allow**, so set the policy explicitly.
- The return-immediately ticket matters here: the front freezes speech until the tool result lands, so a non-blocking tool keeps the freeze to the measured ~1 to 4 s instead of the length of Claude's run.
- Acks: NVIDIA's per-tool on-hold message is spoken verbatim as soon as the call is triggered, **but only in NVIDIA's CUDA container** [vendor]. Soniqo's Mac runtime has no scripted speech and holds speech during tool work. So on a Mac, acks, progress lines and readback all depend on the same unbuilt forced-text patch, or on cached TTS clips played through the same AEC loop.
- Readback: a patch that pushes Claude's tokenised summary into the agent text channel, the way NVIDIA's `_redirect_tokens_queue` does. The patch would need porting to Swift (speech-swift) or the mlx-audio Python port; neither was inspected. The words enter both EAR-TTS (same voice, same Apple AEC loop) and the LLM context, so the front knows what it said [inference]. Cost: one subword per 80 ms frame, so ~45 tokens take ~3.6 s, which is about natural speaking pace.
- Unknown: the result must arrive when the front is idle; whether forcing text mid-listen confuses its turn state is untested.

**Sophon-Realtime Mac (32B Flash-4bit).**
- Delegation: none today. Either wait for the Mearman fork (tool calls into `mac/`, then the Live adapter), or run a side channel: our own ASR on the mic stream (`mlx-audio` Qwen3-ASR, as that fork does) plus an intent rule outside the model.
- Readback: patch `mac/engine.py` to enqueue Claude's text to the talker as a turn that is "already written" [inference]. The vendor's ASR check that speech follows the text word for word is the best evidence of any candidate that the path is faithful.
- Watch issue #15 for an official `say`.
- Strength: the best conversational brain on a Mac, which matters for the chit-chat around Claude's work.

**Duopra.** It is wired exactly as the brief describes (`query(task)` with an OpenAI-compatible backend URL), so a thin OpenAI-compatible shim in front of the Agent SDK would drop in. But it runs only on CUDA, and it paraphrases results ("Done, it's $99"). It is not usable on the M5 Max without porting the runtime to llama.cpp-omni or vllm-metal.

**Separate TTS (fallback, works with any front).**
- Route Claude's summary to a local TTS via mlx-audio. Per `2-tts-models.md`, no local open model ships an Australian preset: use Qwen3-TTS VoiceDesign ("Australian male, relaxed") or a consented clone. Kokoro is US/UK only.
- Duck or mute the front's output while it plays.
- Feed the TTS audio into the **same AEC reference** as the front's output. If you don't, the front hears Claude's summary as the user talking.
- Tell the front what was said, as a tool result or injected text, so its next turn has the context.

## Ranked top 3 for this design

1. **NemotronLabs VoiceChat 11B via soniqo speech-swift.**
   - It is the only candidate that runs on a Mac **today** with all four of full duplex, a native tool channel, MCP and AEC.
   - It has independent Apple Silicon measurements (M5 Pro, RTF 0.92).
   - NVIDIA's own code shows how to force exact text through its voice. It fits in ~9 GB, leaving the M5 Max plenty of headroom.
   - Weaknesses: a 9B brain with FDB v3 Pass@1 33%, so it will sometimes misroute or forget to delegate; speech freezes during tool waits; English only; no published speaker-mode AEC test.
2. **Sophon-Realtime Mac 32B Flash-4bit.**
   - It has the best open conversational quality, with VoiceBench 82.8, built-in AEC3 on speakers, and a Python engine whose talker already reads given text word for word.
   - Ranked second because Mac delegation exists only in a community fork, all Mac numbers are vendor-run on an M4 Max with simulated audio, there is an open licence-provenance issue, and the project is 18 days old.
   - It could overtake VoiceChat within weeks if the fork's tool calling merges and #15 adds `say`.
3. **Duopra / Realtime-Venus lineage, as a watch item.**
   - Its delegation is the best-designed of any candidate: RL-trained to delegate, silent mid-sentence calls, and async results.
   - Not runnable on a Mac today, and the MiniCPM-o talker lineage measurably drops reply tails, which is the opposite of verbatim.
   - Revisit if someone ports it to llama.cpp-omni or vllm-metal, now that MiniCPM-o 4.5 duplex runs there.

Not ranked: Haru-4B (no instruction following, no tools), LFM3 duplex (non-commercial, ~1.2 s pickup, headphones only), Moshi/PersonaPlex (no tools), and anything hosted.

## Fallback if verbatim readback fails

If the forced-text patch on VoiceChat or Sophon gives garbled audio, a WER over a few percent on paths and numbers, or broken turn state:
- **Keep the duplex front for conversation only** (acks, "still working", barge-in, small talk).
- **Speak Claude's summaries through a separate local TTS**, using the AEC-reference rule above.
- **The front's barge-in detector cancels that TTS and can call `interrupt()` on the Agent SDK.**

If even that is too fiddly, drop to the plain cascade from reports 1 to 4: `huggingface/speech-to-speech` on a Mac (Parakeet + Smart Turn + Qwen3.5-4B MLX + Qwen3-TTS, OpenAI Realtime protocol, tool calls). Use a tiny local LLM as router, and have the TTS read Claude's text directly. That gives up full-duplex feel but guarantees verbatim.

## Afternoon experiments on the M5 Max

Each needs installs (brew, uv, model downloads ~10 to 30 GB). Name them in the plan so the permission classifier sees them: `brew install speech` (soniqo CLI, macOS 15+; or `make build` in a speech-swift checkout); `bash mac/install.sh` in sophon-realtime; `uv tool install mlx-audio`. Mise/uv rules apply to the Python pieces.

1. **VoiceChat delegation loop (2 h).**
   - Run `speech voice-chat --mcp-config <file> --mcp-write-policy deny` with an MCP config that exposes a stub `ask_claude_code` (returns a ticket in 200 ms) and `status`, both read-only. 
   - Script 20 spoken requests: 10 that should delegate, 5 that should not, and 5 with mid-sentence corrections.
   - Measure: RTF on the M5 Max; misrouted or missed calls; freeze length; self-interruption on **laptop speakers** vs headset; whether corrected arguments survive.
   - Pass: RTF < 0.85, ≥ 9/10 delegated, 0 self-interrupts on speakers.
2. **Verbatim fidelity test (2 h; the one that decides the design).**
   - Take 20 real Claude Code Stop-hook summaries rich in paths, identifiers, numbers and version strings.
   - Speak each through (a) a forced-text patch into VoiceChat's agent channel (first check whether the mlx-audio Python port exposes the text channel at all, since that port was not inspected; Swift is the other route); (b) Sophon Mac's talker queue; (c) Kokoro/Qwen3-TTS via mlx-audio as the baseline.
   - Transcribe with local Parakeet; score WER and exact match on the critical tokens.
   - Pass: within 1 point of the TTS baseline, and no dropped tails.
3. **Sophon Mac live-mic reality check (1 h).**
   - Install 32B Flash-4bit and run `--lang en --log turns.jsonl` on laptop speakers.
   - Record the speak-after-stop latency over 20 turns, barge-in stop time, and self-interrupts. Post the numbers to issue #1, which no one with an M5 Max has yet done.
   - Optionally check out `Mearman/sophon-realtime@feat/mac-tool-calling` and repeat experiment 1's routing test.

## Biggest uncertainty

Whether forcing text into a duplex model's speech channel keeps its turn-taking state coherent. Nobody has published this on a Mac: NVIDIA uses it only for short redirects and acks, and Sophon's word-for-word claim is about the model's own text. Second: every Mac latency figure is on an M4 Max or M5 Pro, mostly hot-compute or simulated audio. None is a live microphone on laptop speakers on an M5 Max.

## Sources (all read 2026-11-22 unless stated)

- Sophon-Realtime: https://github.com/adventists-ai/sophon-realtime ; `mac/README.md` ; `live/README.md` ; `CHANGELOG.md` ; issues #1, #3, #5, #15 (gh CLI) ; https://huggingface.co/adventists-ai/Sophon-Realtime-4B-Flash-MLX ; fork branches via `gh api repos/Mearman/sophon-realtime/branches`
- Duopra: https://huggingface.co/Chechen123/Duopra ; https://github.com/cyChen2003/duopra ; arXiv 2611.25773
- Realtime-Venus: https://huggingface.co/inclusionAI/Realtime-Venus (arXiv 2609.13814)
- NemotronLabs VoiceChat: https://huggingface.co/nvidia/NVIDIA-NemotronLabs-VoiceChat-11B ; NeMo source `nemo/collections/speechlm2/inference/model_wrappers/nemotron_voicechat_inference_wrapper.py` @ branch `nemotron-labs-voicechat` (lines cited above) ; `examples/speechlm2/function_calling/template.jinja`
- Soniqo / speech-swift: https://soniqo.audio/voice-agents ; https://soniqo.audio/guides/speech-to-speech ; https://blog.ivan.digital/nvidia-nemotron-voicechat-on-apple-silicon-full-duplex-speech-with-tools-6165625d55c4 (2026-09-10)
- Haru: https://huggingface.co/higurashi-ai/Haru-4B ; https://github.com/higurashi-ai/Haru ; https://pypi.org/project/haru-speech-mlx/ (2026-11-13)
- mlx-audio: https://github.com/Blaizzy/mlx-audio (now Neywa-Labs) ; https://pypi.org/project/mlx-audio/ (0.6.5, 2026-11-09)
- Liquid: https://huggingface.co/LiquidAI/LFM3-Omni-2B-MLX-8bit ; https://huggingface.co/MAdel121/LFM3-Audio-2B-Full-Duplex
- MiniCPM-o: https://github.com/OpenBMB/llama.cpp-omni ; https://github.com/tc-mb/llama.cpp-omni/issues/134 ; https://github.com/vllm-project/vllm-metal ; https://github.com/OpenSQZ/MiniCPM-V-CookBook (WebRTC demo hardware table)
- huggingface/speech-to-speech: https://github.com/huggingface/speech-to-speech
- MOSS-Live: https://github.com/OpenMOSS/MOSS-Live ; Shizuku: https://shizuku.ai/en/blog/1/?full=20261108 ; landscape table: https://research.getbluejay.ai/whitepapers/voice-ai-landscape (2026-11-15)
- Benchmarks: https://www.fullduplex.ai/benchmarks/fdb-v1 ; https://www.fullduplex.ai/benchmarks/fdb-v3 ; https://www.fullduplex.ai/knowledge/choosing-a-model (2026-11-12) ; https://github.com/DanielLin94144/Full-Duplex-Bench ; https://aclanthology.org/2026.emnlp-main.2331.pdf
- Others: https://huggingface.co/keyvan-ai/Saturn-Duplex-5B-DE ; https://huggingface.co/KRAFTON/Raon-SpeechChat-9B ; https://huggingface.co/naklecha/caramel-1 ; https://huggingface.co/inclusionAI/Duo-1.0-distill ; https://huggingface.co/Trelis/duplex-0
- HF API sweeps: `api/models?search={duplex,full-duplex,speech-to-speech,omni-mlx,realtime,voicechat,moshi}&sort=lastModified` and `pipeline_tag={audio-to-audio,any-to-any}&sort=trendingScore`

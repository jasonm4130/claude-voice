# Voice layer x Claude Code: integration surfaces and prior art

Research snapshot, November 2026. Figures are from the cited sources unless marked as measured; nothing here was benchmarked by this project.

Docs read 2026-11-21/22 (code.claude.com). Repo stats via `gh` on 2026-11-22.

## 0. Built-in voice (as of Nov 2026)
- Claude Code has `/voice` = dictation only (STT into the prompt, hold/tap Space, `voice.autoSubmit` setting, rebindable via `voice:pushToTalk`). Transcription runs on Anthropic's servers, needs a claude.ai login (not API key/Bedrock), 20 languages. Also works in agent view peek/reply and the VS Code extension.
- No spoken replies in Claude Code. Support article: "In Claude Cowork and Claude Code, dictation is available but voice mode isn't" (the claude.ai/mobile two-way voice mode does not drive Claude Code).
- So the open gap is TTS output plus hands-free turn-taking. Local STT is also open (built-in is cloud).

## 1. Integration surfaces

| Surface | Streaming tokens out? | Inject input into a LIVE interactive session? | Effort | Notes |
|---|---|---|---|---|
| `Stop` hook (command/http) | No; fires at end of turn. Payload has `last_assistant_message` (final text), `transcript_path`, `session_id`, `effort`, `background_tasks`. Docs explicitly say use this field for read-aloud hooks, not the transcript (transcript may lag) | Can block/continue via `decision`, `additionalContext`, not a voice path | Very low | Best cheap TTS-on-finish. Latency = whole reply. Hook runs async OK (`async: true`); hooks must return fast |
| `Notification` hook | No | No | Very low | `message` + `notification_type` (e.g. `permission_prompt`). Use to speak "needs approval" |
| `UserPromptSubmit` hook | No | Can rewrite/add context, block. Fires on turns Claude Code starts itself | Low | `prompt` field. Good for tagging "this was spoken" so Claude replies in spoken style |
| `MessageDisplay` hook (new) | Fires "while assistant message text is displayed"; `hookSpecificOutput.displayContent` replaces display text only; 10 s default timeout; no matcher | No | Low | Possibly per-message chunk, which could give pre-Stop TTS. UNVERIFIED how granular; needs a 10-minute experiment |
| `PostToolUse`/`PreToolUse` hooks | No | No | Low | Progress narration ("running tests"). `PermissionRequest` event also exists |
| Output style / CLAUDE.md | n/a | n/a | Trivial | Make replies short, speakable, no tables/code; put a 1-2 sentence "spoken summary" first. This is the main quality lever for TTS |
| Status line | Polled, not a stream | No | Low | Only for a listening/speaking indicator |
| MCP server (VoiceMode `converse` style) | Claude calls a tool; tool speaks text and blocks while recording the user's answer. Streaming only as far as the model writes the tool arg | Indirect: Claude must call the tool; the user speech comes back as the tool result. Not usable to interrupt a running turn | Medium | VoiceMode's model. Fragile: cancelled converse calls leave playback running / disconnect Claude Code (open issues Oct 2026) |
| Channels (`claude --channels`, MCP server with `experimental['claude/channel']`) | Claude replies via a `reply` tool (text per call, not token stream) | YES. `notifications/claude/channel` pushes an event into the already-running local session, arrives as `<channel>` message. Two-way with reply tool; can relay permission prompts (`claude/channel/permission`, "yes abcde" verdicts) | Medium | Official, documented path for chat bridges (Telegram/Discord/iMessage). Needs claude.ai login + session opt-in flag; org controls on Team/Enterprise. Sender gating is your job. Best fit for "voice daemon pushes transcript into a real session and speaks the reply tool call". Marked research-preview-ish; confirm status |
| Mods (plugin with JS hooks inside Claude Code) | Can follow a turn (`Follow a turn` events), draw panes | YES: docs list "submit a prompt as if you had typed it" and send message to another session. softcery voice-relay uses a mod that long-polls a local server and submits tasks as prompts | Medium | Early-access API, can change. Runs in terminal/Desktop/VS Code; `claude -p`/SDK run the hooks but draw nothing. In-process so most powerful, least stable |
| `claude -p --output-format stream-json --verbose --include-partial-messages` | YES: `stream_event` `text_delta` tokens, then final `result` | `--input-format stream-json` keeps stdin open for further user messages in ONE headless session (not an existing interactive TUI) | Medium | TapQ uses this (Claude as stream-json delegate). Loses the TUI. `--resume <id>` can pick up a TUI session by id later, but not concurrently |
| Agent SDK (TS `query()` w/ async generator; Python `ClaudeSDKClient`) | YES: partial messages / text deltas; `interrupt()` for barge-in; messages sent mid-tool-call are delivered after tool calls finish (or `priority`) | Own your session (headless). Can `resume` a session id | Medium | Cleanest for a custom voice app and barge-in. Proven by larryhudson/claude-code-voice-agent (LiveKit `llm_node` -> ClaudeSDKClient) and Pipecat's "Voice Code Assistant" example (voice LLM + Claude Agent SDK code agent) |
| Remote Control / mobile / Dispatch | Streams to claude.ai/app | YES but only from Anthropic's clients (claude.ai/code, mobile app); no public API to drive it from your own voice daemon | n/a | Phone use case: Remote Control app has dictation; replies are text. Not a hook point. Needs claude.ai login, no custom base URL |
| `tmux send-keys` / PTY wrapper (`heard run`) | Parses terminal output | YES, crude: type into the pane | Low-medium | Works with any agent version; brittle on TUI redraws. Heard uses it only as fallback |
| Apple dictation / Superwhisper / VoiceInk / Wispr typing into the terminal | No | YES, trivially (keystrokes into whatever has focus) | Zero | Gives STT with zero integration. Superwhisper also has a CLI that pipes transcripts into Claude Code and a macOS add-on that notifies on finish + voice reply (per iravoice, Jul/Oct 2026; vendor claim) |

Key facts to design around
- Final text: use `Stop.last_assistant_message`, not the transcript.
- Barge-in/interrupt is only first-class in the SDK (`interrupt()`) and channels/mods can abort by sending a new prompt (voice-relay does "stop, then new instructions").
- Permission prompts block a voice session: voice-relay says its agent "cannot answer permission prompts"; TapQ reads them aloud and takes a spoken yes/no; channels have an official permission-relay.
- Hooks must not block: Heard returns immediately and has a daemon speak asynchronously.

## 2. Prior art

Stars/pushed from `gh` 2026-11-22 (Parallel excerpts for descriptions).

| Project | Stars | Last push | License | Approach | Verdict |
|---|---|---|---|---|---|
| mbailey/voicemode | 1,472 | 2026-11-20 | MIT | MCP `converse` tool + plugin; local Whisper.cpp + Kokoro or OpenAI; silence-detect VAD; 2,302 commits; 30 open issues | Most mature and active. Local-capable. Issues: voice-server SIGSEGV in audio callback, Bluetooth HFP loses first word, 65 GB uv cache from `uvx --refresh`, cancel leaves playback running, no barge-in yet (PR offered), macOS 27 scipy dlopen failure. Same authors now push Session Kit. ADOPT-to-trial or mine for ideas |
| sessionkit/sessionkit (+sessionvoice etc.) | 2 | 2026-11-17 | AGPL-3.0 | VoiceMode authors' successor: voice, phone (Delta Chat), agent mail, tmux; alpha 0.4.0, needs tmux/ffmpeg/notmuch, ~8 GB | Too early, AGPL, heavy. Watch only |
| softcery/claude-code-voice-relay | 1 | 2026-11-19 | MIT | Claude Code plugin = mod + Pipecat server (localhost:7860). Voice LLM with tools `send_task`/`abort`/`open_session`; multi-session; read-back before commit/push. Local options: Moonshine/Whisper STT, Ollama/LM Studio LLM, Kokoro/Piper TTS | Best architectural match (separate voice agent in front of a session, local-capable, barge-in-ish). Brand new (1 star); depends on mods early-access API; can't answer permission prompts; local engines slower and mishear names. FORK/study |
| spaceamoeba-t/tapq | 648 | 2026-10-30 | Apache-2.0 | Swift CLI; Claude Code as stream-json child + Codex app-server; OpenAI Realtime for STT/TTS, small LLM routes intents; spoken permission requests; journal per folder | Good design (deterministic gate: answer only counts if request heard in full). Cloud-only (OpenAI key), pins Claude Code 2.1.260-2.1.293, 0.6.0 rewrite dropped on-device speech. Study, don't adopt |
| heardlabs/heard | 994 | 2026-11-20 | Apache-2.0 (engine; app closed) | Hooks (Stop/Pre/PostToolUse/UserPromptSubmit) -> daemon -> Kokoro/ElevenLabs; summarises instead of reading all; PTY wrapper; talk-back is paid closed-app feature | Strong TTS-only reference; local Kokoro, never blocks agent. Analytics on by default in engine (toggle). Input half is closed/paid. Reuse ideas, not product |
| Null-Phnix/claude-voice | 40 | 2026-11-01 | MIT | Stop hook -> daemon -> local Kokoro (or OpenAI/ElevenLabs/xAI); karaoke highlighting; strips code/URLs; skips code-heavy replies | Closest to "minimal TTS hook". Small, fine as template |
| dhuynh95/duck_talk | 27 | 2026-09-16 | MIT | Voice layer wrapping Claude Code as a black box; Gemini Live to hear, streaming TTS sentence by sentence; review mode shows transcript before it runs; correction learning | Good UX ideas (review-before-send, sentence streaming). Cloud models |
| aayushdebugging/claude-voice | 10 | 2026-07-11 | MIT | Node wrapper around `claude` CLI; sentence-level streamed TTS; barge-in; Groq Whisper + ElevenLabs | Low adoption, cloud |
| larryhudson/claude-code-voice-agent | 2 | 2025-12-12 | none stated | LiveKit agent, custom `llm_node` -> Claude Agent SDK `ClaudeSDKClient`; AssemblyAI STT, Cartesia TTS | Reference for SDK + LiveKit wiring; stale, cloud |
| Pipecat example "Voice Code Assistant" | (pipecat 17,368 stars, BSD-2, pushed 2026-11-21) | active | BSD-2 | Voice agent + code agent using Claude Agent SDK tools | Framework option for a custom build |
| livekit/agents | 15,298 | 2026-11-21 | Apache-2.0 | Voice agent framework, turn detector, interruption handling | Heavier infra than Pipecat for local-only |
| ethanplusai/jarvis | 1,016 | 2026-09-10 | "other" | Mac voice assistant for Claude Code on subscription, no API key | Stale since Sep; licence unclear. Skip |
| abracadabra50/claude-code-voice-skill | 173 | 2026-07-25 | MIT | Phone-call skill | Not relevant for local desk use |
| ZeldOcarina/claude-code-voice-notifications, PeonPing/peon-ping (5,120) | 13 / 5,120 | 2026-11 | - | Notification sounds/ElevenLabs lines on hook events | Notification-only; shows demand |
| eladcandroid/claude-code-voice | 7 | 2026-03-30 | - | Apple SFSpeechRecognizer proxy for built-in `/voice` for unsupported languages | Shows built-in /voice STT can be proxied; niche |

Dictation apps (STT-only, system-wide typing; work in any terminal)
| App | Model | Price (vendor pages, Oct-Nov 2026) | Notes |
|---|---|---|---|
| Superwhisper | local Whisper or cloud, closed | Free tier; Pro US$8.49/mo, $84.99/yr, $249.99 once | Has Claude Code integration (finish notification + voice reply; CLI that pipes transcript) per third-party guide; closed |
| VoiceInk (Beingpax) | local whisper.cpp, Apple silicon | $25 one-time; 7,176 stars, pushed 2026-11-11 | GPL-3 (GitHub shows "other"); can build from source free |
| OpenSuperWhisper (Starmel) | local | free, MIT, 3,166 stars, pushed 2026-11-17 | Open alternative |
| Handy | local, free, cross-platform | free | Named best free local option in a Jul 2026 comparison |
| Wispr Flow | cloud only | $15/mo | Cloud; avoid if local-only is required |
| Apple Dictation | on-device if enhanced dictation enabled | free | Weak on technical terms, per Qiita comparison |
| Claude Code `/voice` | Anthropic cloud | included, needs claude.ai login | Free STT, nothing local |

Complaints seen: names/jargon misheard by local STT (voice-relay, Apple dictation); echo/self-interruption without headphones (voice-relay); Bluetooth headset drops first word (VoiceMode issue 2026-10-30); permission prompts stall hands-free flows (voice-relay, TapQ designs around it); reading a full reply aloud is too long, so tools summarise (Heard, TapQ, claude-voice skip code-heavy replies); API pin churn (TapQ pins Claude Code versions; mods are "early access").

## 3. Recommended architecture

Build a thin custom layer, borrowing from voice-relay/TapQ/Heard, rather than adopting VoiceMode wholesale. Reasons: a local-first layer that works in real interactive sessions with hooks/plugins is a poor fit for VoiceMode, whose MCP-converse model needs Claude to call a tool each turn, has no barge-in, and has open stability bugs; voice-relay is 1 star and rides an unstable API; Heard's input half is closed.

Phase 1 (an afternoon, zero risk): output + input separate.
- Input: keep `/voice` or run VoiceInk/OpenSuperWhisper/Handy (local) typing into the terminal. Optional later: `voice.autoSubmit`.
- Output: a `Stop` hook (async, returns instantly) that POSTs `last_assistant_message` to a local daemon (launchd) which strips code/tables/URLs, optionally summarises with a local small model or the "first sentence" convention, and speaks via local TTS (Kokoro/Piper/Pocket TTS). Add a `Notification` hook to speak permission requests. Add a short CLAUDE.md/output-style rule: "start every reply with a one-sentence spoken summary; no tables in that sentence". Fork Null-Phnix/claude-voice (MIT) or Heard's engine (Apache) as the starting point.

Phase 2 (hands-free loop in the real session): channel plugin.
- Write a small MCP channel server (documented contract, `claude --channels`) fed by a local always-on daemon: mic -> VAD -> local STT (Whisper/Parakeet-class, model choice is covered in report 1) -> `notifications/claude/channel`; replies come back through the `reply` tool and are spoken sentence by sentence; permission relay used for spoken "yes/no <id>". Gate on sender (localhost token). This injects into the live interactive session, keeps hooks, CLAUDE.md, MCP and subagents intact.
- If channels prove unavailable (login/org gating) fall back to a mod that submits prompts (voice-relay's trick) or tmux send-keys.

Phase 3 (only if token-level latency or barge-in matters): headless session owner via Agent SDK.
- Daemon owns a `ClaudeSDKClient`/`query()` generator session, streams `text_delta` into a sentence splitter -> TTS, calls `interrupt()` on VAD barge-in, `resume`s by session id. Pipecat gives VAD/turn-taking/interruption plumbing (larryhudson and Pipecat's Voice Code Assistant are the references). Cost: you lose the TUI; use `claude --resume` to attach later.

Do not: build around Remote Control (no API), or MCP-converse as the primary loop.

## 4. Biggest uncertainties
1. Channels maturity and gating: it requires claude.ai login and an opt-in flag, and the docs read as a preview. Needs a 30-minute spike to confirm a locally spoken transcript lands in an interactive session without the Telegram-style pairing flow, and that the permission relay works with a local sender.
2. `MessageDisplay` hook granularity: if it fires per streamed chunk it gives sentence-level TTS inside the normal TUI with no SDK; docs excerpt does not say. Also 10 s timeout.
3. Mods API stability (early access) if Phase 2 falls back to it.
4. Superwhisper's Claude Code add-on details come only from a third-party comparison (iravoice), not vendor docs.
5. Anthropic terms for driving a subscription login via another tool (TapQ README flags this; check before Phase 3 with a claude.ai login).

## 5. Sources
- https://code.claude.com/docs/en/voice-dictation
- https://code.claude.com/docs/en/hooks
- https://code.claude.com/docs/en/headless
- https://code.claude.com/docs/en/channels
- https://code.claude.com/docs/en/channels-reference
- https://code.claude.com/docs/en/remote-control
- https://code.claude.com/docs/en/plugins/mods/overview
- https://code.claude.com/docs/en/agent-sdk/streaming-vs-single-mode
- https://support.claude.com/en/articles/11101966-using-voice-mode-on-claude
- https://code.claude.com/docs/en/feature-availability
- https://github.com/mbailey/voicemode (+ issues list via gh)
- https://github.com/sessionkit/sessionkit
- https://github.com/softcery/claude-code-voice-relay
- https://github.com/spaceamoeba-t/tapq
- https://github.com/heardlabs/heard
- https://github.com/Null-Phnix/claude-voice
- https://github.com/dhuynh95/duck_talk
- https://github.com/aayushdebugging/claude-voice
- https://github.com/larryhudson/claude-code-voice-agent
- https://docs.pipecat.ai/pipecat/examples/overview
- https://github.com/pipecat-ai/pipecat , https://github.com/livekit/agents
- https://iravoice.com/guides/best-dictation-app-for-claude-code (2026-07-26)
- https://enjoy.dev/blog/voice-dictation-claude-code-codex (2026-11-08)
- https://parrotnotes.app/blog/superwhisper-vs-wispr-flow (2026-10-22)
- https://superwhisper.com/vs/voiceink
- https://qiita.com/DevMasatoman/items/2043d28b291f00f8e5b0 (2026-04-24)

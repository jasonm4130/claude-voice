# 7. Voice UX for a coding agent (researched 2026-11-22)

Research snapshot, November 2026. Figures are from the cited sources unless marked as measured; nothing here was benchmarked by this project.

Warning up front: Claude Code's built-in /voice is input only (dictation into the prompt). Everything spoken back is DIY or third-party. The one claim in this doc with no source behind it is that a spoken "yes" can be made safe; every source says it cannot be on its own.

## Frame
A voice-agent failure taxonomy says the listener's mental model is the only durable artefact of a voice exchange (sounds vanish, only the model in the listener's head accumulates). Design consequence for a coding agent: speak LESS, in a fixed order the listener learns, and always say which session/project is talking and who moves next. Never "speak the transcript". Same source: never feed model output straight to TTS (normalise first); assume ASR is brittle on names/identifiers; collect values into typed fields and validate. (its sources are publisher blurbs, not transcripts.)

## 1. What to speak
Rule of thumb from Nubank's BLIND-CLAUDE.md (2026-09-16, one low-vision user's daily setup, no wider validation): "Every response must make sense read top-to-bottom, out loud, in order." Concrete mappings:

| Artefact | Spoken treatment |
|---|---|
| Code block | Skip. Say what it does in one clause. Never the sole carrier of meaning. |
| Diff | Describe in plain language ("changed the retry limit in the sync worker from three to five"); never read +/- lines. Blind-dev research notes +/- prefixes are read serially and are slow (CHI/ASSETS work, see links). |
| Table | Prose of the winner plus the one trade-off; full table stays on screen. |
| File paths, URLs, hashes, UUIDs | Skip or name by role ("the config file"). If needed, basename only. Heard's /say tests assert no paths/URLs/code are read aloud. |
| Tool calls / logs / test output | Never narrate raw. Reduce to the 2-3 lines that matter, then one sentence. |
| Numbers | Words ("two tests failed", not "2/14"). Digit strings (ports, ids) spell digit by digit only if essential. |
| "See above/below" | Forbidden; restate. |
| Options | Say recommendation + the single trade-off; full comparison on screen ("Too many options to say: recommendation out loud, comparison on screen"). |

Fixed three-part briefing (heardlabs/claude-code-tts, Oct 2026, with a 17-scenario eval using a judge model): 1) Context (which project/session), 2) Outcome (done/failed/blocked/going + the one fact that matters), 3) Next action + owner (never end without an owner). Length tiers: short <=15 words, default <=35 (50 if a decision is needed), long <=80. Decision wording: options, one trade-off, recommendation, "your call".

Normalisation rules for the TTS layer (belt and braces after summarisation): strip markdown; expand identifiers only when they must be said (snake_case -> "snake case words", camelCase split); expand acronyms by a pronunciation dictionary (CI, PR, k3s, pnpm, mise, SQL, ASCII...); units spelled out, locale conventions (for example metric units, day/month dates, local time zone); strip all-caps words (one reported case: all-caps "TACO!" misread as "Takeo" by a local Qwen3-TTS; rewriting as "Taco!" fixed it). Add a per-user pronunciation list (speak MCP by CareyScott has add_pronunciation). Validate by ASR round trip.

## 2. Summarisation approach (recommendation)
Three options exist in the wild:
A. Raw last message, markdown stripped, capped (say hook; 600 chars). Cheap, but reads noise. Reject as default.
B. Claude writes the spoken part itself (agent-voice: UserPromptSubmit hook injects an instruction, reply ends with a <spoken> block, Stop hook speaks it; also /say skill). Highest fidelity because the main model has the full context, no extra latency/cost, but adds tokens to every reply and relies on instruction following. agent-voice also prefixes MEASURED facts (diff stats, tests really passed) and flags when the model claims success over red tests - a good guard against the spoken summary being optimistic.
C. Separate cheap model (Haiku) rewrites last_assistant_message at Stop. Decoupled from the main prompt, so text mode is unchanged; costs a call and ~1s; sees only the final message not tool results unless you feed them (the transcript may not contain the final message at Stop; docs recommend last_assistant_message).

Recommendation: B as primary (a "spoken" block, three-part template, in an output style or a UserPromptSubmit-injected reminder, only when voice mode is on), with C as fallback when the block is missing or malformed, and deterministic facts (exit codes, test counts, files changed count) injected by the hook rather than trusted from the model. Haiku-class is plenty for C. Stream sentence by sentence to TTS (speak MCP does: playback starts on first sentence).
Per Anthropic's prompting guidance (official doc): give the reason behind a rule - the official example is "no ellipses because a text-to-speech engine reads the output". So the instruction should say "this will be read by TTS" plus the reason for each rule, not a bare list. I found no dedicated Anthropic voice-output doc beyond that; treat as an uncertainty.

## 3. When to speak
Claude Code gives the hooks (docs: code.claude.com/docs/en/hooks):
- Stop: Claude finished. Gets last_assistant_message. Not fired on user interrupt; API errors use StopFailure (a separate event).
- PermissionRequest: fires the moment a dialog would appear (immediate). Notification/permission_prompt only fires after ~6 s unattended and each keystroke defers it; idle_prompt ~60 s after finish if you have not typed. Also elicitation_dialog (MCP form), agent_needs_input, agent_completed.
Policy (adapting agent-voice's "intent tone + attention policy", Aloud's "alerts and short gists", claude-speak's opt-in per session):
1. Always speak, short: needs you (permission, question, elicitation), failed/blocked, finished a long task (>~60 s or when you walked away).
2. Earcon only (no words): finished a short task, or finished while you are looking/typing. Distinct tones for done / question / blocked / failed (agent-voice). Microsoft research quote from blind developers: "Too many text prompts can actually interfere with my code comprehension... sound effects help."
3. Silent: mid-turn tool chatter, successful intermediate steps, subagent completions, anything while you are speaking or typing.
4. Progress for long runs: one line at milestones or every N minutes, only if the run was started by voice; never per tool call. (claude-code-narrator narrates tool steps; judged noisy for this use - my inference, not tested.)
5. Presence gating: speak only if away from the keyboard (idle > ~6 s) or in conversation mode. Offer two modes: Notification mode (default: tones + context sentence) and Conversation mode (full duplex, VoiceMode-like, replies in briefing style, ends when you say "stop" or go quiet). Per-session on/off, parallel sessions queue not overlap and each opens with its project name (heardlabs).
6. Keep text identical on screen so the briefing can be re-read; interruption/"stop"/"shush" global kill (agent-voice, speak pill).
7. Spoken replay command: "say that again", "more detail" (speak skill has styles: simple, brief, decisions, full, eli5; back one sentence).

## 4. Speaking to Claude
- Claude Code /voice: hold-to-record or tap-to-record dictation into the prompt, mixable with typing; works in agent view to dictate to background sessions (docs: code.claude.com/docs/en/voice-dictation). No spoken reply. Mixed-input fits: dictate prose, type or paste identifiers.
- Identifier problem: ASR is brittle on proper nouns, code-switching, identifiers (failure taxonomy above). Talon's answer is a grammar: formatter words ("camel one two three" -> oneTwoThree), phonetic alphabet, and a custom vocabulary file for words that misfire (additional_words.csv / words_to_replace.csv). For an LLM-driven pipeline the cheaper version: (a) pass a keyterm/vocab list to ASR from the repo (file names, package names, project names, from git ls-files / package.json) - raise probability, not guarantee; (b) tell Claude the prompt came from dictation and may contain homophone errors in identifiers, and to resolve against the repo (grep) before acting; (c) when a dictated identifier does not exist, say so and offer the nearest match rather than create it; (d) keep a replace-map for recurring mishears ("pee en pee em" -> pnpm).
- Correction: Talon has "correct that", "replace X with Y", "cancel cancel", and "over" to end a command. Equivalent here: show transcript before sending (push-to-talk then review) for first weeks; "scratch that" cancel; "no, I said X" handled by Claude re-reading the last prompt. Typed fields with validators for anything structured (paths, branch names, numbers).
- Commands vs dictation: Talon's command mode vs dictation mode is a real lesson; mis-transcription may be vocabulary matching, not mishearing. A small reserved command set ("stop", "yes/approve", "no/deny", "say again", "go quiet") separate from free dictation avoids prompts that start "stop" being swallowed.

## 5. Permission prompts by voice: safety
Evidence: every source treats a bare spoken "yes" as weak. WorkOS (2026-09-22): voice has no out-of-band channel; a spoken yes binds to a model-generated narration, not the exact tool arguments; speech cannot prove who is speaking. DEV (2026-11-14, "The TV Said Yes"): confirm with something tied to the specific action; reject speech that started before the question ended. Check Point (2026-10-29): audio can carry hidden/ambient instructions; ASR can be attacked. CHI 2026 study: screen-reader developers moved over time from enthusiasm for full automation toward features that require user confirmation.
Design:
1. Classify by risk (read / reversible / destructive / external). Read and in-repo reversible: auto-allow via existing permission rules, no voice involvement. Destructive, external (push, send, spend, delete, prod) need confirmation anyway.
2. Voice can say what is being asked (PermissionRequest hook): the tool, the one risky parameter in words, the consequence ("run a command that deletes the build folder in the billing repo. Say 'approve delete' to allow"). Not "are you sure?".
3. Confirmation token tied to the action: for reversible-but-notable, a short phrase naming the verb ("approve push"); for destructive/external, do NOT accept voice alone - require keypress/click (or a typed word) while voice reads the proposal. Voice approves, keyboard or a second factor commits. This is a recommendation; I found no tested design of this for coding agents.
4. Hardening: accept only after the prompt finishes speaking (ignore barge-in-before-question), timeout default-deny (~15-30 s), single-use, wake/push-to-talk required (no open mic), echo cancellation so Claude's own TTS and media cannot answer, ignore if the voice-activity speaker changed (if diarisation is available). Never let content from tool output or the web be spoken as if it were a user instruction.
5. Safe default for ambiguity: deny and re-ask once, then fall back to the terminal.
6. Log every voice approval with transcript + action id.

## 6. Prior art (checked 2026-11-22)
- heardlabs/claude-code-tts - /say briefing template + Stop hook; has eval harness. https://github.com/heardlabs/claude-code-tts
- HalbonLabs/agent-voice - <spoken> block, measured-facts prefix, intent tones, attention policy, per-session state. https://github.com/HalbonLabs/agent-voice
- hopchouinard/claude-speak - passive Stop speech + active mid-turn speech, opt-in per session, dedupe. https://github.com/hopchouinard/claude-speak
- CareyScott/speak - MCP, styles, pronunciation dictionary, streaming, controls. https://github.com/CareyScott/speak
- mbailey/voicemode - two-way conversation via MCP converse tool (~1.5k stars), local Whisper.cpp + Kokoro. https://github.com/mbailey/voicemode
- Comparison page (vendor-authored by Heard, treat as marketing): https://heard.dev/compare/claude-code-text-to-speech
- Claude Code dictation: https://code.claude.com/docs/en/voice-dictation ; hooks: https://code.claude.com/docs/en/hooks
- Nubank BLIND-CLAUDE.md: https://building.nubank.com/designing-claude-for-ears-not-eyes-an-accessibility-skill-for-blind-and-low-vision-users
- CHI 2026 screen-reader programmers in vibe coding: https://dl.acm.org/doi/10.1145/3772318.3790726 ; ASSETS 2025 heuristics: https://dl.acm.org/doi/10.1145/3663547.3759729 ; Microsoft Research: https://www.microsoft.com/en-us/research/articles/microsoft-study-shows-ai-assistants-help-with-development-for-programmers-who-are-blind-or-have-low-vision/ ; diff audio affordances: https://dl.acm.org/doi/fullHtml/10.1145/3597638.3614550
- Talon: https://talon.wiki/Voice%20Coding/formatters/ ; commands https://talonvoice.com/docs/reference/voice-control.html ; field notes https://www.fileside.app/blog/2025-04-14_voice-computing
- Voice safety: https://dev.to/aqibnawab/the-tv-said-yes-confirming-risky-actions-in-voice-agents-41ca ; https://workos.com/blog/voice-ai-agent-authorization ; https://blog.checkpoint.com/ai-security/audio-guardrails-voice-agents/ ; https://portal.raidguild.org/wiki/voice-controlled-agent-safety-patterns

## Uncertainties
1. No source measured whether <spoken> blocks by the main model beat a separate Haiku rewrite; B vs C is a reasoned choice, cheap to A/B with heardlabs' eval approach.
2. No tested design of voice approvals for coding agents; section 5 is synthesis from phone-agent and general voice-agent security writing.
3. Most prior-art claims come from READMEs (and one vendor comparison page); none were run by me. No Anthropic doc on voice output beyond the TTS-ellipsis example.
4. The Nubank rules reflect one user and no feedback yet (their own caveat). The right amount of speech varies by person; make verbosity a setting.

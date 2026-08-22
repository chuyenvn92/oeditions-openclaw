# OpenClaw session organization

Last reviewed: 2026-08-20.

Use this as the operating pattern for the private Discord workspace. The goal is
to keep Xu and Ve Thang useful as a chief-of-staff pair without burning tokens
on unrelated context.

## Channel boundaries

Each Discord channel should map to one durable work area:

- `#research-desk`: outside research, market scans, source collection.
- `#code-review`: PRs, diffs, repo questions, technical review.
- `#openclaw-config`: bot setup, permissions, persona changes, VPS ops.
- `#video-maker`: the video/content side project.
- `#demo-stage`: clean rehearsal channel for the talk; reset or archive old
  threads before presenting.
- `#general`: quick questions and triage only.

If a side project becomes active for more than a few messages, give it its own
channel. If it is a single task inside a project, use a thread inside that
project channel.

## Session rules

- New project, new channel.
- New task inside the same project, new thread.
- Same task but long context, summarize the state before continuing.
- Noisy or confused answers mean context pollution is likely. Make a brief:
  goal, decision so far, relevant links/files, next action, blockers.
- Save durable decisions and preferences into KB; do not rely on old Discord
  history as memory.

## Agent roles

- Xu is the router and chief-of-staff front desk: quick triage, reminders,
  research summaries, KB recall/save, and tight handoffs.
- Ve Thang is the deep-work partner: planning, code reasoning, long reviews,
  and final synthesis when a task needs more than a quick pass.
- Tho should stay quiet unless the human tags it directly. It is a specialist,
  not an ambient participant.

## Privacy pattern

Treat OpenClaw like a new employee identity, not like the owner. Prefer separate
accounts and scoped data:

- Use an assistant-owned email identity for side-project signups and public
  operations. Do not connect the user's real Gmail by default.
- Put side-project files/notes into curated KB documents, not raw personal
  stores.
- Give scripts narrow read-only access first, then add writes only when the
  workflow has a clear review boundary.

## Handoff brief format

When Xu asks Ve Thang for help, keep it tight:

```text
Goal:
Context:
Constraints:
Known links/files:
Decision needed:
Next action requested:
```

This is cheaper than forwarding long chat history and produces better answers.

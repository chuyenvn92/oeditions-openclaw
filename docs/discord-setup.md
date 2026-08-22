# One Discord room, several model bots

The target: a private server where `🪙 Xu` (DeepSeek), `🔧 Thợ` (Qoder), and
`🎫 Vé Tháng` (Codex) all sit in the same workspace.
Tagging one of them assigns the work to that role. Review does not rely on
Discord bots tagging each other; that path was tested and failed. Cross-review
happens through OpenClaw agent-to-agent consults or the review script.

## How OpenClaw maps onto that

| Piece | Mechanism |
| --- | --- |
| One bot per model | One Discord application per bot; each has its own token and its own OpenClaw agent (`openclaw agents add`) |
| Tag to assign | Group mention gating. `groupPolicy: "allowlist"`, replies require a mention — untagged messages are kept as context only, so every bot reads the room but only the tagged one answers |
| Cross review | Agent-to-agent consults (`sessions_send`); Discord bot-to-bot mentions are not the production path |
| Loop safety | Pair loop protection: 20 events per 60s sliding window per bot pair, then a 60s cooldown, both directions |
| Blast radius | Per-agent `tools.deny`, **but only over OpenClaw's own tools** — see the correction below. Docker sandboxing was tried and is now `off`: it reported `runtime: sandboxed` while the agent ran on the host as the logged-in user |

All of these are already written to `~/.openclaw/openclaw.json`.

## Correction 2026-08-16: `tools.deny` does not reach a CLI backend

This document used to say tool denial "is the boundary that actually holds, and
it cannot fail open". That is wrong, and the gateway log shows why:

```text
tool policy removed 6 tool(s) via agents.<cli-agent>.tools.deny:
  apply_patch, cron, edit, exec, process, write
cli exec: provider=<cli-backend> model=<cli-model>
```

OpenClaw removes the six tools from its own surface, and two seconds later hands
the turn to a CLI backend running in a terminal with its own command surface.
The deny list never names that inner tool surface and cannot reach it.

The lesson applies to the current CLI-backed specialists (`qoder-cli` for Thợ
and `codex-cli` for Vé Tháng): assume any CLI-backed agent can do what the
logged-in Linux user can do.

So the deny list is real for agents on an API backend and cosmetic for agents on
a CLI backend. Same family as the sandbox note above: a control that reports
success while the agent runs on the host as the logged-in user.

Two consequences worth carrying into the demo. Scope every instruction narrowly
— "run the master step on this file" rather than "tidy up" — because there is
nothing underneath to catch a misread. And expect turns to be slow: measured
18s, 55s and 165s on real requests, the long one being a full pipeline step.

## Known risk: cross review may not work at all

[openclaw#11199](https://github.com/openclaw/openclaw/issues/11199) reports that
with several agent bots on one instance, OpenClaw treats **every** configured
bot account as "self" and filters it, so bot A's mention never reaches bot B.
Filed 7/2/2026 against 2026.2.3-1, closed 8/3 as **stale — not fixed**.

The version here (2026.7.1-2) ships `allowBots: "mentions"` and pair loop
protection keyed on `(account, channel, bot pair)`, both of which only make
sense if bot-to-bot delivery works. No changelog entry confirms a fix either
way.

**So test this with two bots before building any more.** Have bot A mention bot
B and watch whether B answers. Either outcome is worth having: it works, or you
have reproduced a live repo bug with a version number. Here it reproduced
(openclaw#11199), which is why the room leans on agent-to-agent consults
instead.

## What only you can do

Repeat for each bot, at <https://discord.com/developers/applications>:

1. **New Application**, name it after the model.
2. **Bot** tab → set the username → enable **Message Content Intent**
   (required; without it the bot receives empty message bodies).
3. **Reset Token** → copy it. Despite the wording this mints the first token.
4. **OAuth2** → URL Generator → scopes `bot` and `applications.commands` →
   under Bot Permissions tick at least View Channels, Send Messages, Read
   Message History → open the generated URL → invite into the private server.

Three core bots means three applications and three tokens. One shared private
server is enough.

## What runs after the tokens exist

Save each token to its own file rather than pasting it into a terminal or a
chat window, then:

```bash
openclaw agents add deepseek --non-interactive \
  --workspace "$HOME/.openclaw/workspaces/deepseek" \
  --model deepseek/deepseek-chat
openclaw agents add qoder --non-interactive \
  --workspace "$HOME/.openclaw/workspaces/qoder" \
  --model qoder-cli/auto
openclaw agents add codex --non-interactive \
  --workspace "$HOME/.openclaw/workspaces/codex" \
  --model codex-cli/gpt-5.4

scripts/add-bot.sh deepseek xu-bot       ~/discord-xu.token
scripts/add-bot.sh qoder    thoi-bot     ~/discord-thoi.token
scripts/add-bot.sh codex    ve-thang-bot ~/discord-ve-thang.token
openclaw agents list --bindings
openclaw channels status
rm ~/discord-*.token
```

`add-bot.sh` does `channels add` plus `agents bind` and prints the verification
commands. It reads the token from a file so it never enters shell history, but
passes it inline to `channels add`, because that command rejects `--token-file`
with "Discord requires token". OpenClaw then stores it in plain text in
`openclaw.json` regardless, so the file handling buys less than it looks.

Check `agents list --bindings` rather than assuming: a Discord account with no
binding does not fail, it quietly falls through to the default agent. Confirm
that all three accounts (`xu-bot`, `thoi-bot`, `ve-thang-bot`) route
to their intended agents.

## Mention ids are still useful

A bot cannot mention another bot without its numeric Discord id, so local
deployments may keep ids in the prompt for diagnostics and fallback
experiments. They live in `personas/ROSTER.md`, which
`scripts/apply-personas.sh` writes into every agent's `AGENTS.md` between
`ROSTER:BEGIN`/`ROSTER:END` markers.

For a shared repo, keep placeholders in `personas/ROSTER.md` and put the real
ids in `personas/ROSTER.local.md` on the deployed machine. That file is ignored
by git, and `scripts/apply-personas.sh` prefers it when present. The ids are not
tokens, but they still identify your Discord applications and do not belong in
public project history.

Keep that table honest: an id that outlives the bot it was labelled with sends
every agent's work to the wrong model, and nothing errors.

Two more ways that table and the persona files can go wrong, both silent:

**A roster that omits a member is read as a menu, not as an incomplete list.**
One agent had no Discord app yet, so it was left out of the table. Asked its own
name, it answered with a *colleague's* role — it had read the roster, failed to
find itself, and picked the nearest fit. List every agent in the room even when
it has no id; write "no Discord bot yet" in the id column rather than omitting
the row.

**`IDENTITY.md` never reaches a CLI-backed agent.** `openclaw agents list` prints
`Identity: 🎫 Vé Tháng (IDENTITY.md)` for the agent, and OpenClaw has plainly
read the file — but the model has not seen it. Probing for something only that
file carries: one CLI agent named a colleague's emoji as its own and then
*deduced* its billing model from the roster by elimination; another said outright
it did not know which bot it was mapped to. `AGENTS.md` does arrive. So
`apply-personas.sh` now inlines the identity into `AGENTS.md` behind
`IDENTITY:BEGIN`/`END` markers — redundant for API-backed agents, and the only
copy a CLI-backed one ever sees.

Same shape as the sandbox above and the deny list below: **the surface that tells
you the persona is loaded is not the surface that loads it.** The test that
catches it is never "does the config look right" — it is asking the agent
something only the file in question could have told it.

**Mention ids must be copied, not recalled.** One agent emitted an id with a
single digit changed. It renders as a perfectly ordinary mention, reaches nobody,
and logs nothing.

## Current state

- Agents in the room: `main`, `deepseek`, `qoder`, `codex`. The three
  model agents have Discord bots; `main` catches unbound traffic.
- Personas applied to the bot agents (`apply-personas.sh`).
- Access to the room is one Discord user id on the guild allowlist. That, not
  the tool denies, is what stops anyone else from reaching these bots at all.
- **Do not set `plugins.allow`.** It reads like the fix for the auto-load
  warning and it is an absolute allowlist: it took enabled plugins from 32/33 to
  most auto-loaded providers and can break unrelated model routes later.

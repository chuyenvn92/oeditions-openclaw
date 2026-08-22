# Runbook — template

This is a public-safe runbook template. Keep real instance names, billing ids,
guild ids, user names, and bot ids in a private note or deployment-specific
patch, not in this repo.

## What is where

| | |
| --- | --- |
| Instance | `<instance-name>`, zone `<zone>`, Ubuntu 24.04 |
| Type | `<machine-type>` |
| Service user | `openclaw` (dedicated Linux user, no access to personal home dirs) |
| Gateway | systemd **user** unit `openclaw-gateway`, lingering enabled |
| Gateway bind | `127.0.0.1:18789` — never `0.0.0.0` |
| Repos on server | `<repo-path>` |
| Billing | Track this in your cloud console/private ops notes, not in git |

## Getting in

```bash
gcloud compute ssh <instance-name> --zone <zone>
sudo -u openclaw -i                                        # become the service user
```

Almost every command below must run as `openclaw`. From your personal user,
`Permission denied` on the agent's files is the isolation working, not a fault.

## The room

| Discord bot | Account | Agent | Model | Pays how |
| --- | --- | --- | --- | --- |
| 🪙 Xu | `xu-bot` | `deepseek` | `deepseek/deepseek-chat` | API key |
| 🔧 Thợ | `thoi-bot` | `qoder` | `qoder-cli/auto` | personal token |
| 🎫 Vé Tháng | `ve-thang-bot` | `codex` | `codex-cli/gpt-5.4` | ChatGPT subscription |

Access should be restricted to one private guild, any channel in it, mentions
only. Keep the real guild id out of git.
Heartbeat is `0m` on defaults, so no agent wakes itself.

Codex can run shell commands here; Qoder cannot. Qoder stops at its own
permission prompt — `Permission confirmation required but no interactive handler
is available`, seen in its session log on 17/8.

Codex could not either until 18/8: its bubblewrap sandbox cannot create a
namespace on this VM, so `--sandbox read-only` failed before it ever reached the
command. The backend now carries `--dangerously-bypass-approvals-and-sandbox`,
and with it `codex exec` runs normally — measured, `sandbox: danger-full-access`,
`approval: never`.

Read that as what it is. `tools.deny` never reached a CLI backend to begin with,
so the sandbox was the last control in the stack, and it is now off by choice.
What remains is the guild/user allowlist. Anything Vé Tháng is asked to run, it
runs as `openclaw`. Scope requests narrowly, and give it a script name rather
than a command line to assemble.

### Checking the room

```bash
openclaw channels status                 # connection per bot
openclaw agents list --bindings          # which account routes to which agent
openclaw agent --agent deepseek --session-key t --message "Trả lời: OK"
```

Status output proves the config, not the running process. **Bindings are read
when the gateway starts**, so after changing one, restart and then confirm with
real traffic:

```bash
openclaw daemon restart
# tag a bot in Discord, then:
openclaw sessions list --all-agents --json \
  | python3 -c "import json,sys; [print(s['key']) for s in json.load(sys.stdin)['sessions'] if 'discord:channel' in s['key']]"
```

A session key of `agent:main:...` means the binding did not load.

## Credentials

| What | Where |
| --- | --- |
| Discord bot tokens | `~/.openclaw/openclaw.json` on the server, plain text, mode 600 |
| DeepSeek API key | `~/.openclaw/openclaw.json`, under `models.providers` |
| Qoder token | `~/.openclaw/secrets.env`, read by `~/qoder-cli.sh` |
| Codex | ChatGPT OAuth, `codex login --device-auth`; check expiry/status on the VPS |

When Codex expires, `codex login --device-auth` as `openclaw`, then approve the
printed code from any browser.

## When something is wrong

| Symptom | Cause to check first |
| --- | --- |
| Bot online but silent | Wrong channel, or a binding added after the gateway started |
| Bot answers as the wrong model | Binding not loaded — restart, then verify with traffic |
| `FailoverError: Unknown model` | Provider plugin missing; compare `models list` with `models list --all` |
| `plugins.allow is empty` warning | Ignore it. Setting it disables the stock providers |
| An exported variable has no effect | Put it in `~/.profile`, not `~/.bashrc` |

One command worth knowing, read-only:

```bash
openclaw channels logs --channel discord --lines 200
```

In the Discord log, every bot account that was *not* mentioned writes its own
`no-mention` line. With three accounts: three such lines means nobody was tagged
(usually a name typed as text instead of picked from autocomplete); two means
one bot accepted it.

# Moving the room to a VPS

Why you would: the bots stop depending on one laptop being awake, and a
CLI-backed agent gets a machine it is allowed to own rather than your own
(see the `tools.deny` correction in [discord-setup.md](discord-setup.md) — deny
lists do not reach a CLI backend, so the boundary has to be the box itself).

Discord bots connect **outbound**. Nothing here needs an open port, a static IP
or a domain.

## Size it from what a turn actually costs

Measured by sampling the RSS of the gateway's own child processes while a turn
ran. An earlier version of this file said 500 MB per turn; that figure came from
grepping process names and had picked up a VS Code extension host, not anything
OpenClaw spawned. Measure descendants of the gateway pid, or measure nothing.

| Backend | Extra per turn | Child processes |
| --- | --- | --- |
| API (`deepseek/deepseek-chat`) | HTTP call, low local memory | none |
| CLI `qoder` | 39 MB | 1 |
| CLI `codex` | measure on the VPS before demo | 1 |

Gateway idle: ~410 MB.

The split that matters is not the megabytes, it is the column on the right. An
API-backed turn is an HTTP call; a CLI-backed turn **starts a whole agent
process**. That one fact sets the sizing:

| Room | Concurrent answering pattern | Box |
| --- | --- | --- |
| Xu only (API) | low local memory | 1 GB is enough |
| Full room with Thợ/Vé Tháng active | CLI processes spawn | 2 GB minimum, 4 GB comfortable |

So "you do not need a powerful machine" is true only for the API half. The
subscription/CLI trick is what needs the bigger box, because it launches another
agent process. Say both halves in the talk.

## One bot token, one gateway

Two gateways holding the same Discord token fight over the session: duplicated
replies, random disconnects. Before starting the VPS gateway, stop the laptop's:

```bash
openclaw daemon stop           # on the laptop
```

Treat this as a cutover, not a mirror. Running both "just in case" is the one
configuration guaranteed to misbehave.

## Order of operations

Steps marked **TTY** need an interactive terminal — SSH is fine, a script is
not. This order is the one that worked on a box already running something else;
the notes are what actually went wrong, not what might.

**0. Give it its own Linux user.** If the box runs anything you care about, this
is the step that matters most, because a CLI-backed agent can do whatever its
user can. Prove the boundary rather than assuming it:

```bash
sudo useradd -m -s /bin/bash openclaw
sudo -u openclaw ls /home/you     # expect: Permission denied
```

**1. Node ≥ 22.22.3, for that user only.** Do not touch the system Node if
another service depends on it. nvm's installer is fetched from GitHub raw, which
answered `429` here; the official tarball avoids that and needs no installer:

```bash
sudo -u openclaw -H bash -lc '
  VER=v22.23.2   # or the current v22 from https://nodejs.org/dist/index.json
  curl -fsSL https://nodejs.org/dist/$VER/node-$VER-linux-x64.tar.xz -o /tmp/node.tar.xz
  mkdir -p ~/node && tar -xJf /tmp/node.tar.xz -C ~/node --strip-components=1
  echo "export PATH=\$HOME/node/bin:\$PATH" >> ~/.bashrc'
```

OpenClaw notices an unsupported system Node and uses this one for the daemon,
and says so. That is the one place in this whole stack where the version trap
announces itself.

**2. Enable lingering, then install and onboard.** A systemd *user* service
cannot be installed over `sudo -u`: onboarding exits 1 with "systemd user
services are unavailable". Lingering gives that user a persistent systemd
instance, and it is also what makes the gateway come back after a reboot.

```bash
sudo loginctl enable-linger openclaw
# then, with XDG_RUNTIME_DIR=/run/user/$(id -u openclaw) exported:
npm install -g openclaw@latest
openclaw onboard --non-interactive --accept-risk \
  --mode local --auth-choice skip \
  --gateway-port 18789 --gateway-bind loopback \
  --install-daemon --daemon-runtime node \
  --skip-channels --skip-skills --skip-search --skip-hooks --skip-ui
```

Keep `--gateway-bind loopback`. On a laptop that is a detail; on a rented box it
is the difference between a local service and one on the public internet. To
reach the dashboard, SSH-tunnel it (`ssh -L 18789:127.0.0.1:18789 …`) or turn on
Tailscale. Do not bind `0.0.0.0`.

**3. Copy the agent workspaces.** Personas, identities and room rules live
outside this repo:

```bash
rsync -a ~/.openclaw/workspaces/ vps:~/.openclaw/workspaces/
```

Then clone this repo on the VPS and run `scripts/apply-personas.sh` to keep them
in sync from here on.

**4. Regenerate the CLI backend paths.** The patch names absolute commands
because launchd/systemd give the gateway a minimal PATH:

```bash
scripts/render-cli-backends.sh
openclaw config patch --file config/cli-backends.generated.patch.json5 --dry-run
openclaw config patch --file config/cli-backends.generated.patch.json5
openclaw config patch --file config/qoder-replaces-pplx.patch.json5
```

**4b. Install the DeepSeek provider plugin.** Xu is API-backed —
`deepseek/deepseek-chat`, not the CLI — so this step is required.
`deepseek/deepseek-chat` can appear in `openclaw models list --all` with the
key set and still fail at call time with `FailoverError: Unknown model`. The
catalogue lists models; a *plugin* serves them, and DeepSeek's is not bundled:

```bash
openclaw plugins search deepseek
openclaw plugins install clawhub:@openclaw/deepseek-provider
openclaw daemon restart
openclaw models list          # deepseek/* only appears here once the plugin is in
```

`models list --all` is the catalogue, `models list` is what is actually
configured. Comparing the two is how you tell a missing plugin from a bad key.

After installing it, every command prints `plugins.allow is empty; discovered
non-bundled plugins may auto-load`. **Leave it alone.** Following that advice
turns the field into an absolute allowlist and disables the stock providers —
32/33 enabled to 2/68, with the breakage surfacing hours later somewhere
unrelated.

To use the CLI backend (`deepseek-cli/deepseek-v4-flash`) instead of the API,
skip this plugin and let `render-cli-backends.sh` pick up the `deepseek`
binary — see `config/cli-backends.generated.patch.json5`.

**5. Authenticate the models.**

- **DeepSeek, Qoder** — Put the DeepSeek API key in `~/.openclaw/openclaw.json`
  (under `models.providers`) or environment, and put the Qoder token in `.env`
  or `~/.openclaw/secrets.env`.
- **Codex** — `codex login --device-auth` **(TTY, on the VPS)**. It prints a code
  to approve from any other device. Do not copy `~/.codex/auth.json` across:
  it works until it silently does not, which is the worst failure mode to
  inherit.

Check before moving on:

```bash
codex login status        # expect: Logged in using ChatGPT
```

**6. Create and attach the bots.** Three agents and three bot tokens, one file
each:

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
rm ~/discord-*.token
```

**7. Create the Discord channel layout.** This is Discord server setup, not an
OpenClaw patch. Keep it small so the audience can understand the system:

| Channel | Purpose |
| --- | --- |
| `#general` | quick triage, short questions |
| `#research-desk` | source finding, verification, market/work research |
| `#openclaw-config` | VPS, bot bindings, permissions, persona changes |
| `#code-review` | PRs, diffs, repo-specific technical review |
| `#demo-stage` | clean end-to-end demo thread for the talk |

Do **not** add these channel ids to `channels.discord.guilds[*].channels` unless
you really need a channel allowlist. The safer default for this private server is
restricting to the guild and one user, then allowing any channel inside that
guild. A new channel that is missing from a channel allowlist fails silently:
the bot receives nothing, logs nothing useful, and looks broken.

**8. Verify with traffic, not with status output.** `agents list --bindings`
showing a route proves the config, not the running process — bindings are read
when the gateway starts, so a binding added afterwards routes to the default
agent while every surface reports success. Restart, then tag each bot and check
which agent actually answered:

```bash
openclaw daemon restart
# tag each bot in Discord, then:
openclaw sessions list --all-agents --json \
  | python3 -c "import json,sys; [print(s['key']) for s in json.load(sys.stdin)['sessions'] if 'discord:channel' in s['key']]"
```

Expect one `agent:<name>:discord:channel:…` per bot you tagged. If you see
`agent:main:…`, the binding did not load.

## The access rules do not travel, and their ids go stale

Nothing in this repo tracks `channels.discord.guilds`. It lives only in
`openclaw.json`, so a fresh onboard has no allowlist at all: the first bot
attached is reachable from any guild it is invited to, by anyone in it. That
matters more here than on a laptop, because a CLI-backed agent does not honour
`tools.deny` — the config key is the whole boundary.

Copying the block over from the old machine is the obvious fix and it is where
the second trap is. The guild id survived the move; the **channel id did not**,
because the room had moved to a different channel. A `channels` map is an
allowlist, and a message in a channel that is not on it is dropped *before the
logging layer* — no reply, no error, and not even the `no-mention` skip line that
every other rejected message produces. Watching the log for it is watching for
something the code has already thrown away.

So: never port an id, read it. With the restriction lifted, one working message
puts the real ids in the log:

```bash
grep -o '"channelId\\?":\\?"[0-9]*' /tmp/openclaw/openclaw-*.log | sort -u
```

And prefer restricting to the **guild**, not to a list of channels. The guild is
the real boundary — a private server you control. A channel allowlist adds very
little on top of it and fails silently every time someone opens a new channel,
which is exactly the failure you cannot debug from the symptom.

## What does not come with you

`plugins.entries.openclaw-code-agent.config.defaultWorkdir` points at a repo on
the laptop. On the VPS that path does not exist, so coding tasks and anything
that runs project scripts stop working until you either move that repo too or
point the plugin somewhere real on the server.

Chat, review and the prompt-driven workflows are unaffected — they touch no
files.

## Before a live demo

- Measure a real turn on the VPS. On the laptop they ran 18s, 55s and 165s; a
  smaller box will not be faster, and the first time you learn the number should
  not be on stage.
- Keep screenshots of two working exchanges. Venue networks are the one part of
  this that no configuration fixes.

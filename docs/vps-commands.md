# VPS command cheat sheet — template

Public-safe ops commands for a deployed OpenClaw VPS. Replace every value in
angle brackets with your own instance, zone, paths, and channel ids.

## Connect

```bash
gcloud compute ssh <instance-name> --zone=<zone>
sudo -u openclaw -i
cd <repo-path>
```

## Edit secrets safely

Do not paste API keys into Discord. Put them in the VPS secrets file:

```bash
nano ~/.openclaw/secrets.env
chmod 600 ~/.openclaw/secrets.env
systemctl --user restart openclaw-gateway.service
```

Add keys as shell env lines:

```bash
AGENTMAIL_API_KEY="..."
```

## Gateway status

```bash
openclaw channels status --probe
```

Short service checks:

```bash
systemctl --user status openclaw-gateway.service --no-pager
systemctl --user restart openclaw-gateway.service
journalctl --user -u openclaw-gateway.service -n 100 --no-pager
```

## Token/cost report

```bash
cd <repo-path>
./scripts/token-report --days 1 --agent deepseek
./scripts/token-report --days 7 --agent deepseek
./scripts/token-report --days 1 --agent deepseek --json
```

## Open loops

```bash
cd <repo-path>
./scripts/open-loops
./scripts/open-loops-set "Side-Project Inbox Identity" \
  --status "..." \
  --next "..." \
  --channel "#openclaw-config"
```

## Test Xu without posting to Discord

```bash
cd <repo-path>
openclaw agent \
  --agent deepseek \
  --session-key agent:deepseek:manual-smoke \
  --message "Hôm nay đang có open loops nào?"
```

## Test Xu and post to a Discord channel

Find a channel id in Discord developer mode, then replace `<channel-id>` below.

```bash
cd <repo-path>
openclaw agent \
  --agent deepseek \
  --session-key agent:deepseek:discord:channel:<channel-id> \
  --message "Chief-of-staff check: hôm nay đang có open loops nào?" \
  --deliver \
  --reply-channel discord \
  --reply-account xu-bot \
  --reply-to channel:<channel-id>
```

## Discord logs

```bash
openclaw channels logs --channel discord --lines 200
```

## Apply persona changes after editing repo files

```bash
cd <repo-path>
bash scripts/apply-personas.sh
systemctl --user restart openclaw-gateway.service
```

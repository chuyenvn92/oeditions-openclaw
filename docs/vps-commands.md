# VPS command cheat sheet

Private ops notes for the live OpenClaw VPS.

## Connect

```bash
gcloud compute ssh openclaw@REDACTED-VPS-HOST --zone=REDACTED-ZONE
cd /home/openclaw/REDACTED-REPO-PATH
```

## Edit secrets safely

Do not paste API keys into Discord. Put them in the VPS secrets file:

```bash
nano /home/openclaw/.openclaw/secrets.env
chmod 600 /home/openclaw/.openclaw/secrets.env
systemctl --user restart openclaw-gateway.service
```

Add keys as shell env lines:

```bash
AGENTMAIL_API_KEY="..."
```

## Gateway status

```bash
/home/openclaw/node/bin/node /home/openclaw/node/lib/node_modules/openclaw/dist/index.js channels status --probe
```

Short service checks:

```bash
systemctl --user status openclaw-gateway.service --no-pager
systemctl --user restart openclaw-gateway.service
journalctl --user -u openclaw-gateway.service -n 100 --no-pager
```

## Token/cost report

```bash
cd /home/openclaw/REDACTED-REPO-PATH
./scripts/token-report --days 1 --agent deepseek
./scripts/token-report --days 7 --agent deepseek
./scripts/token-report --days 1 --agent deepseek --json
```

## Open loops

```bash
cd /home/openclaw/REDACTED-REPO-PATH
./scripts/open-loops
./scripts/open-loops-set "Side-Project Inbox Identity" \
  --status "..." \
  --next "..." \
  --channel "#openclaw-config"
```

## Test Xu without posting to Discord

```bash
cd /home/openclaw/REDACTED-REPO-PATH
/home/openclaw/node/bin/node /home/openclaw/node/lib/node_modules/openclaw/dist/index.js agent \
  --agent deepseek \
  --session-key agent:deepseek:manual-smoke \
  --message "Hôm nay đang có open loops nào?"
```

## Test Xu and post to a Discord channel

Use channel ids carefully:

- `#code-review`: `REDACTED_CHANNEL_ID`
- `#openclaw-config`: `REDACTED_CHANNEL_ID`
- `#video-maker`: `REDACTED_CHANNEL_ID`
- `#research-desk`: `REDACTED_CHANNEL_ID`
- `#general`: `REDACTED_CHANNEL_ID`
- `#demo-stage`: `REDACTED_CHANNEL_ID`

```bash
cd /home/openclaw/REDACTED-REPO-PATH
/home/openclaw/node/bin/node /home/openclaw/node/lib/node_modules/openclaw/dist/index.js agent \
  --agent deepseek \
  --session-key agent:deepseek:discord:channel:REDACTED_CHANNEL_ID \
  --message "Chief-of-staff check: hôm nay đang có open loops nào?" \
  --deliver \
  --reply-channel discord \
  --reply-account xu-bot \
  --reply-to channel:REDACTED_CHANNEL_ID
```

## Discord logs

```bash
/home/openclaw/node/bin/node /home/openclaw/node/lib/node_modules/openclaw/dist/index.js channels logs --channel discord --lines 200
```

## Apply persona changes after editing repo files

```bash
cd /home/openclaw/REDACTED-REPO-PATH
bash scripts/apply-personas.sh
systemctl --user restart openclaw-gateway.service
```

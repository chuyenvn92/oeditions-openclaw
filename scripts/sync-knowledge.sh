#!/usr/bin/env bash
# Push the curated slice of a local knowledge folder into the VPS and
# re-index it for kb-search / kb-recall.
#
#   scripts/sync-knowledge.sh
#
# Run this from the laptop (needs gcloud + a local notes checkout) whenever
# your knowledge/*.md files change. There is no live connection
# between the VPS and the laptop — this is the explicit, one-command way
# to close that gap, run by hand rather than a fragile cross-machine cron.
set -euo pipefail

ZONE="${ZONE:?set ZONE, e.g. your-cloud-zone}"
INSTANCE="${INSTANCE:?set INSTANCE, e.g. my-openclaw-vps}"
KNOWLEDGE_SRC="${KNOWLEDGE_SRC:?set KNOWLEDGE_SRC to the local folder containing .md notes}"
REMOTE_USER="${REMOTE_USER:-openclaw}"
REMOTE_REPO="${REMOTE_REPO:-/home/$REMOTE_USER/oeditions-openclaw}"
REMOTE_KNOWLEDGE_DIR="${REMOTE_KNOWLEDGE_DIR:-/home/$REMOTE_USER/data/knowledge}"

[ -d "$KNOWLEDGE_SRC" ] || { echo "not found: $KNOWLEDGE_SRC" >&2; exit 1; }

echo "Uploading $(ls "$KNOWLEDGE_SRC"/*.md | wc -l | tr -d ' ') files from $KNOWLEDGE_SRC"
gcloud compute scp "$KNOWLEDGE_SRC"/*.md "$INSTANCE:/tmp/knowledge-sync/" --zone "$ZONE" 2>&1 | tail -5 || {
  gcloud compute ssh "$INSTANCE" --zone "$ZONE" --command "mkdir -p /tmp/knowledge-sync"
  gcloud compute scp "$KNOWLEDGE_SRC"/*.md "$INSTANCE:/tmp/knowledge-sync/" --zone "$ZONE"
}

echo "Replacing ~/data/knowledge/ on the VPS and re-indexing"
gcloud compute ssh "$INSTANCE" --zone "$ZONE" --command '
  sudo mkdir -p '"$REMOTE_KNOWLEDGE_DIR"'
  sudo rm -f '"$REMOTE_KNOWLEDGE_DIR"'/*.md
  sudo cp /tmp/knowledge-sync/*.md '"$REMOTE_KNOWLEDGE_DIR"'/
  sudo chown '"$REMOTE_USER:$REMOTE_USER"' '"$REMOTE_KNOWLEDGE_DIR"'/*.md
  sudo rm -rf /tmp/knowledge-sync
  sudo -u '"$REMOTE_USER"' -H bash -c "
    cd '"$REMOTE_REPO"'/scripts
    python3 kb-index.py
  "
'

echo "Done — kb-search / kb-recall now see the latest knowledge/ notes."

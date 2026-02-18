#!/bin/bash
# Auto-deploy script: pulls latest from GitHub, rebuilds if changed, restarts via pm2.
# Install: crontab -e → */5 * * * * /path/to/survey-app/deploy.sh >> /path/to/survey-app/deploy.log 2>&1

# ── Configuration ────────────────────────────────────────────────────
APP_DIR="$(cd "$(dirname "$0")" && pwd)"
PM2_APP_NAME="survey-app"        # name shown in `pm2 list`
BRANCH="main"                    # branch to track
NOD_ENV="production"            # production or development
LOG_PREFIX="[deploy $(date '+%Y-%m-%d %H:%M:%S')]"

cd "$APP_DIR" || { echo "$LOG_PREFIX ERROR: can't cd to $APP_DIR"; exit 1; }

# ── Pull latest ──────────────────────────────────────────────────────
git fetch origin "$BRANCH" --quiet

LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse "origin/$BRANCH")

if [ "$LOCAL" = "$REMOTE" ]; then
    echo "$LOG_PREFIX Up to date ($LOCAL)"
    exit 0
fi

echo "$LOG_PREFIX Updating $LOCAL → $REMOTE"

git reset --hard "origin/$BRANCH"

# ── Rebuild ──────────────────────────────────────────────────────────
npm install --production=false 2>&1
npm run build 2>&1

# ── Restart ──────────────────────────────────────────────────────────
pm2 restart "$PM2_APP_NAME" 2>&1

echo "$LOG_PREFIX Deploy complete (now at $(git rev-parse --short HEAD))"

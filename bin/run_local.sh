#!/usr/bin/env bash
# RES-67: run the uptime probe from the Mac (launchd, every 5 min) and publish to the gh-pages branch.
# GitHub's `schedule` trigger is throttled to ~1 run per 7h, so it cannot be the clock.
set -euo pipefail
SRC="$(cd "$(dirname "$0")/.." && pwd)"
WORK="$HOME/.resaleiq-status"
REPO="https://github.com/resaleiq/resaleiq-status.git"
GIT=(git -c user.name="Resale IQ probe" -c user.email="probe@resaleiq.dev")
export SSL_CERT_FILE=/etc/ssl/cert.pem   # python.org builds ship no CA bundle
mkdir -p "$WORK/run/site" "$WORK/pub"

# 1. probe (reads previous status.json from the live site, alerts Telegram on state change)
cd "$WORK/run"
cp "$SRC/probe.py" probe.py
python3 probe.py

# 2. publish: one orphan commit on gh-pages, force-pushed, so history does not grow
cd "$WORK/pub"
[ -d .git ] || { git init -q -b gh-pages; git remote add origin "$REPO"; }
cp "$WORK/run/site/status.json" status.json
cp "$SRC/site/index.html" index.html
printf 'status.resaleiq.dev\n' > CNAME
: > .nojekyll
git add -A
if git rev-parse -q --verify HEAD >/dev/null; then A=--amend; else A=; fi
"${GIT[@]}" commit -q $A --allow-empty -m "status $(date -u +%FT%TZ)"
git push -q --force origin gh-pages
echo "published $(date -u +%FT%TZ)"

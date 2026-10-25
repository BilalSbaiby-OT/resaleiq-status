# resaleiq-status

External uptime probe and public status page (status.resaleiq.dev).

- `probe.py` checks `/` and `/api/health` and merges the result into `status.json`.
- `bin/run_local.sh` is the clock: launchd job `dev.resaleiq.status-probe` on the ops Mac runs it every 5 minutes
  (via `with-secrets.sh` for the Telegram alert env) and force-pushes `site/` to the `gh-pages` branch, which Pages serves.
- GitHub Actions `schedule` was dropped (RES-67): it fired about once per 7 hours.
- Log: `~/.resaleiq-status/probe.log`. Staleness watchdog: see RES-67.

## Scheduler (RES-67)
`bin/dev.resaleiq.status-probe.plist` is the launchd job (every 300 s, through `with-secrets.sh`). Install:
`cp bin/dev.resaleiq.status-probe.plist ~/Library/LaunchAgents/ && launchctl load ~/Library/LaunchAgents/dev.resaleiq.status-probe.plist`.
If neither the live Pages `status.json` nor the local copy is readable, the probe exits 2 and publishes nothing
(set `ALLOW_EMPTY_HISTORY=1` only for a deliberate first run).

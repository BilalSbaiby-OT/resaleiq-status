# resaleiq-status

External uptime probe and public status page (status.resaleiq.dev).

- `probe.py` checks `/` and `/api/health` and merges the result into `status.json`.
- `bin/run_local.sh` is the clock: launchd job `dev.resaleiq.status-probe` on the ops Mac runs it every 5 minutes
  (via `with-secrets.sh` for the Telegram alert env) and force-pushes `site/` to the `gh-pages` branch, which Pages serves.
- GitHub Actions `schedule` was dropped (RES-67): it fired about once per 7 hours.
- Log: `~/.resaleiq-status/probe.log`. Staleness watchdog: see RES-67.

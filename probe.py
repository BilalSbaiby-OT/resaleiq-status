#!/usr/bin/env python3
"""Resale IQ external uptime probe (RES-40). Runs on GitHub Actions, outside the production host.

Probes the public endpoints, merges the result into the previous status.json (fetched from the
published Pages site), alerts Telegram on state changes only, and writes site/status.json.
"""
import json, os, sys, time, urllib.request, urllib.error, datetime as dt

BASE = "https://resaleiq.dev"
CHECKS = [("Website", "/"), ("API health", "/api/health")]
PAGES = os.environ.get("STATUS_URL", "https://status.resaleiq.dev")
TOKEN, CHAT = os.environ.get("TELEGRAM_BOT_TOKEN", ""), os.environ.get("TELEGRAM_CHAT_ID", "")
now = dt.datetime.now(dt.timezone.utc)


def fetch(path, tries=3, gap=15):
    """Return (ok, code, ms). Up only if 200 within 10 s; retry so a single blip is not an outage."""
    for i in range(tries):
        t = time.time()
        try:
            req = urllib.request.Request(BASE + path, headers={"User-Agent": "ResaleIQ-StatusProbe/1.0"})
            with urllib.request.urlopen(req, timeout=10) as r:
                r.read(512)
                code = r.status
        except urllib.error.HTTPError as e:
            code = e.code
        except Exception as e:
            code = type(e).__name__
        ms = int((time.time() - t) * 1000)
        if code == 200:
            return True, code, ms
        if i < tries - 1:
            time.sleep(gap)
    return False, code, ms


def telegram(text):
    if not (TOKEN and CHAT):
        print("telegram not configured:", text)
        return
    data = urllib.parse.urlencode({"chat_id": CHAT, "text": text}).encode()
    try:
        urllib.request.urlopen(f"https://api.telegram.org/bot{TOKEN}/sendMessage", data, timeout=20).read()
    except Exception as e:  # never log the URL: it contains the token
        print("telegram send failed:", type(e).__name__)


import urllib.parse  # noqa: E402

def load_prev():
    """Previous status.json: live Pages copy first, then the last local copy. Never start from {}
    when history exists, or one failed fetch wipes the public uptime record (QA RES-90)."""
    for attempt in range(3):
        try:
            return json.load(urllib.request.urlopen(PAGES + "/status.json", timeout=15))
        except urllib.error.HTTPError as e:
            if e.code == 404:  # nothing published yet: genuinely a first run
                break
        except Exception:
            pass
        time.sleep(5)
    try:
        return json.load(open("site/status.json"))
    except Exception:
        pass
    if os.environ.get("ALLOW_EMPTY_HISTORY") != "1":
        print("no previous status.json from Pages or local copy; refusing to publish empty history")
        sys.exit(2)
    return {}


prev = load_prev()
prev_c = prev.get("components", {})
today = now.strftime("%Y-%m-%d")
out = {"checked_at": now.isoformat(timespec="seconds"), "components": {}, "incidents": prev.get("incidents", [])[:50]}
for name, path in CHECKS:
    ok, code, ms = fetch(path)
    p = prev_c.get(name, {})
    days = p.get("days", {})
    d = days.get(today, {"ok": 0, "total": 0})
    d["total"] += 1
    d["ok"] += 1 if ok else 0
    days[today] = d
    days = dict(sorted(days.items())[-90:])
    since = p.get("since", out["checked_at"]) if p.get("up", True) == ok else out["checked_at"]
    out["components"][name] = {"up": ok, "code": code, "ms": ms, "since": since, "days": days}
    if p and p.get("up", True) != ok:
        if ok:
            mins = max(1, int((now - dt.datetime.fromisoformat(p["since"])).total_seconds() // 60))
            telegram(f"RECOVERED: {name} ({BASE}{path}) is back after ~{mins} min")
            for inc in out["incidents"]:
                if inc["component"] == name and not inc.get("end"):
                    inc["end"] = out["checked_at"]
        else:
            telegram(f"DOWN: {name} ({BASE}{path}) returned {code} on 3 tries 15s apart")
            out["incidents"].insert(0, {"component": name, "start": out["checked_at"], "code": str(code)})

os.makedirs("site", exist_ok=True)
json.dump(out, open("site/status.json", "w"), indent=1)
print(json.dumps({k: (v["up"], v["code"], v["ms"]) for k, v in out["components"].items()}))
if not all(c["up"] for c in out["components"].values()):
    print("::warning::a component is down")

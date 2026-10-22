"""Uptime Monitor — timed health checks with a persistent log.

Deterministic checker (no LLM needed), read-only. Different from
deploy_checker/bug_hunter: it TIMES every request, appends each result to
uptime_log.jsonl (a real history Cyrus can review), and flags anything
slower than 10 seconds. Downtime proposes an URGENT approval.
"""
import json
import os
import time
import urllib.request

from agents.learn import get_lessons, log_run

NAME = "uptime_monitor"
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_FILE = os.path.join(BASE, "uptime_log.jsonl")
TIMEOUT = 15
SLOW_SECONDS = 10

URLS = [
    ("app_homepage", "https://app.victoriatourandadventure.com/"),
    ("main_site", "https://victoriatourandadventure.com/"),
    ("usa_subdomain", "https://washington.victoriatourandadventure.com/"),
    ("knowledge_file", "https://app.victoriatourandadventure.com/api/victoria-knowledge.txt"),
]


def _check(label, url):
    start = time.time()
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "CyrusFactory/2.1"})
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            r.read(20000)
            status = r.status
        elapsed = time.time() - start
        ok = status == 200 and elapsed <= SLOW_SECONDS
        detail = f"HTTP {status} in {elapsed:.1f}s"
        if elapsed > SLOW_SECONDS:
            detail += f" - SLOW (over {SLOW_SECONDS}s)"
        return {"check": label, "ok": ok, "detail": detail,
                "seconds": round(elapsed, 1), "status": status}
    except Exception as e:  # noqa: BLE001 - report honestly per URL
        elapsed = time.time() - start
        return {"check": label, "ok": False,
                "detail": f"DOWN after {elapsed:.1f}s: {e}",
                "seconds": round(elapsed, 1), "status": None}


def run():
    lessons = get_lessons(NAME)
    results = [_check(label, url) for label, url in URLS]

    # persist to the log - real history, append-only
    stamp = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            for res in results:
                f.write(json.dumps({"t": stamp, **res}, ensure_ascii=False) + "\n")
        logged = True
    except OSError as e:
        logged = f"log write failed: {e}"

    down = [r for r in results if r["status"] != 200]
    slow = [r for r in results if r["status"] == 200 and r["seconds"] > SLOW_SECONDS]

    run_id = log_run(NAME, f"timed check of {len(URLS)} URLs",
                     f"{len(results) - len(down)}/{len(results)} up, "
                     f"{len(slow)} slow, log={logged is True}")
    proposed = []
    for r in down:
        proposed.append({
            "title": f"URGENT: {r['check']} is DOWN",
            "kind": "ops",
            "detail": f"{r['detail']}\nURL: "
                      f"{dict(URLS)[r['check']]}\n(Approve = assign an urgent fix task)",
        })
    for r in slow:
        proposed.append({
            "title": f"Slow response: {r['check']} took {r['seconds']}s",
            "kind": "ops",
            "detail": r["detail"],
        })
    summary = (f"{len(results) - len(down)}/{len(results)} up"
               + (f", {len(slow)} slow" if slow else ""))
    return {
        "ok": not down,
        "summary": summary,
        "details": {"results": results, "log_file": LOG_FILE,
                    "run_id": run_id, "lessons_seen": lessons["outcomes_seen"]},
        "proposed_approvals": proposed,
    }

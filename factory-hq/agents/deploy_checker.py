"""Deploy Checker — live HTTP checks that key surfaces are up.

Deterministic checker (no LLM needed), read-only:
  1. App homepage: HTTP 200 + "Cyrus AI" marker
  2. Main website: HTTP 200
  3. USA Tours subdomain: HTTP 200
  4. App service worker: HTTP 200 + cache version marker
Failures propose a fix task in the approval queue.
"""
import re
import urllib.request

from agents.learn import get_lessons, log_run

NAME = "deploy_checker"
TIMEOUT = 15

CHECKS = [
    {"id": "app_home", "url": "https://app.victoriatourandadventure.com/",
     "marker": "Cyrus AI"},
    {"id": "main_site", "url": "https://victoriatourandadventure.com/",
     "marker": None},
    {"id": "usa_site", "url": "https://washington.victoriatourandadventure.com/",
     "marker": None},
    {"id": "app_sw", "url": "https://app.victoriatourandadventure.com/sw.js",
     "marker": "vta-shell-v"},
]


def _get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "CyrusFactory/2.0"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return r.status, r.read(60000).decode("utf-8", errors="replace")


def run():
    lessons = get_lessons(NAME)
    findings = []
    for c in CHECKS:
        try:
            status, body = _get(c["url"])
            ok = status == 200 and (c["marker"] is None or c["marker"] in body)
            detail = f"HTTP {status}" + (
                f", marker '{c['marker']}' {'found' if c['marker'] in body else 'MISSING'}"
                if c["marker"] else "")
            findings.append({"check": c["id"], "ok": ok, "detail": detail})
        except Exception as e:
            findings.append({"check": c["id"], "ok": False,
                             "detail": f"fetch failed: {e}"})

    failed = [f for f in findings if not f["ok"]]
    run_id = log_run(NAME, "live deploy checks",
                     f"{len(findings) - len(failed)}/{len(findings)} up")
    proposed = []
    for f in failed:
        proposed.append({
            "title": f"Deploy Checker: {f['check']} is down ({f['detail'][:60]})",
            "kind": "ops",
            "detail": f["detail"],
        })
    return {
        "ok": not failed,
        "summary": f"{len(findings) - len(failed)}/{len(findings)} deploy checks passed",
        "details": {"findings": findings, "run_id": run_id,
                    "lessons_seen": lessons["outcomes_seen"]},
        "proposed_approvals": proposed,
    }

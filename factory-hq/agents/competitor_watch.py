"""Competitor Watch — HTTP-checks competitor URLs for status changes.

Deterministic checker (no LLM needed): reads competitors.json, fetches each
URL (read-only, small read), reports HTTP status. Downtime or errors propose
an investigation task in the approval queue.
"""
import json
import os
import urllib.request

from agents.learn import get_lessons, log_run

NAME = "competitor_watch"
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COMPETITORS_FILE = os.path.join(BASE, "competitors.json")
TIMEOUT = 15


def _get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "CyrusFactory/2.0"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        r.read(20000)
        return r.status


def run():
    lessons = get_lessons(NAME)
    with open(COMPETITORS_FILE, encoding="utf-8") as f:
        competitors = json.load(f)

    findings = []
    for c in competitors:
        try:
            status = _get(c["url"])
            ok = status == 200
            findings.append({"site": c["name"], "ok": ok,
                             "detail": f"HTTP {status}"})
        except Exception as e:
            findings.append({"site": c["name"], "ok": False,
                             "detail": f"unreachable: {e}"})

    failed = [f for f in findings if not f["ok"]]
    run_id = log_run(NAME, f"check {len(competitors)} competitor sites",
                     f"{len(findings) - len(failed)}/{len(findings)} up")
    proposed = []
    for f in failed:
        proposed.append({
            "title": f"Competitor Watch: {f['site']} looks down ({f['detail'][:60]})",
            "kind": "market",
            "detail": f["detail"],
        })
    return {
        "ok": not failed,
        "summary": (f"{len(findings) - len(failed)}/{len(findings)} competitor sites up"),
        "details": {"findings": findings, "run_id": run_id,
                    "lessons_seen": lessons["outcomes_seen"]},
        "proposed_approvals": proposed,
    }

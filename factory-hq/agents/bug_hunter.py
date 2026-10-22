"""Bug Hunter — real live health checks for Cyrus AI surfaces.

Checks (all read-only, no credits spent):
  1. App homepage reachable (HTTP 200)
  2. App service worker served + cache version marker
  3. Main website reachable (HTTP 200)
  4. Staged knowledge file present locally with sections A-N markers

Returns a dict the factory brain turns into activity log entries and,
on failure, approval-queue proposals.
"""
import os
import re
import urllib.request

TIMEOUT = 15
APP_HOME = "https://app.victoriatourandadventure.com/"
APP_SW = "https://app.victoriatourandadventure.com/sw.js"
MAIN_SITE = "https://victoriatourandadventure.com/"
KNOWLEDGE_FILE = os.path.expanduser(
    "~/workspace/your_files/knowledge-update/victoria-knowledge.txt"
)


def _get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "CyrusFactory/1.0"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return r.status, r.read(60000).decode("utf-8", errors="replace")


def run():
    findings = []
    failures = []

    # 1. App homepage
    try:
        status, body = _get(APP_HOME)
        ok = status == 200 and "Cyrus AI" in body
        findings.append({
            "check": "app_homepage", "ok": ok,
            "detail": f"HTTP {status}, 'Cyrus AI' marker {'found' if 'Cyrus AI' in body else 'MISSING'}",
        })
        if not ok:
            failures.append("App homepage unhealthy")
    except Exception as e:
        findings.append({"check": "app_homepage", "ok": False, "detail": f"fetch failed: {e}"})
        failures.append(f"App homepage unreachable: {e}")

    # 2. Service worker version
    try:
        status, body = _get(APP_SW)
        m = re.search(r"vta-shell-(v\d+)", body)
        ver = m.group(1) if m else "unknown"
        ok = status == 200 and ver != "unknown"
        findings.append({
            "check": "app_sw_version", "ok": ok,
            "detail": f"HTTP {status}, cache version {ver} (expected v23)",
        })
        if ver != "v23":
            failures.append(f"sw.js is {ver}, expected v23 — deploy may be stale")
    except Exception as e:
        findings.append({"check": "app_sw_version", "ok": False, "detail": f"fetch failed: {e}"})
        failures.append(f"sw.js unreachable: {e}")

    # 3. Main site
    try:
        status, body = _get(MAIN_SITE)
        ok = status == 200
        findings.append({"check": "main_site", "ok": ok, "detail": f"HTTP {status}"})
        if not ok:
            failures.append("Main site unhealthy")
    except Exception as e:
        findings.append({"check": "main_site", "ok": False, "detail": f"fetch failed: {e}"})
        failures.append(f"Main site unreachable: {e}")

    # 4. Staged knowledge file sections
    try:
        with open(KNOWLEDGE_FILE, encoding="utf-8") as f:
            text = f.read()
        sections = sorted(set(re.findall(r"SECTION ([A-N])\b", text)))
        ok = sections == list("ABCDEFGHIJKLMN")
        findings.append({
            "check": "knowledge_sections", "ok": ok,
            "detail": f"{len(text)} bytes, sections found: {''.join(sections)}",
        })
        if not ok:
            failures.append(f"Knowledge file sections incomplete: {''.join(sections)}")
    except Exception as e:
        findings.append({"check": "knowledge_sections", "ok": False, "detail": f"read failed: {e}"})
        failures.append(f"Knowledge file unreadable: {e}")

    proposed_approvals = []
    for f in failures:
        proposed_approvals.append({
            "title": f"Bug Hunter: {f}",
            "kind": "bugfix",
            "detail": "Found by Bug Hunter live check. Approve to assign a fix task, reject to dismiss.",
        })

    return {
        "ok": not failures,
        "summary": f"{len([x for x in findings if x['ok']])}/{len(findings)} checks passed",
        "details": findings,
        "proposed_approvals": proposed_approvals,
    }

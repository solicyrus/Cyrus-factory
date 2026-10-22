"""Backup Guard — verifies backup copies exist for critical files.

Deterministic checker (no LLM needed), read-only. For each critical file
it reports size + age in days, then looks for a backup copy next to it
(*.bak, *-old*, *~, *_backup*, or a backups/ folder). Missing or stale
(older than 7 days) backups propose a refresh task. It never creates
backups itself - Cyrus approves the proposal first.
"""
import glob
import os
import time

from agents.learn import get_lessons, log_run

NAME = "backup_guard"
BASE = os.path.dirname(os.path.abspath(__file__))
STALE_DAYS = 7

CRITICAL = [
    os.path.expanduser("~/workspace/your_files/knowledge-update/victoria-knowledge.txt"),
    os.path.join(BASE, "factory_state.json"),
    os.path.join(BASE, "app.py"),
]

BACKUP_SUFFIXES = [".bak", "-old", "~", "_backup", ".backup"]


def _find_backup(path):
    directory = os.path.dirname(path)
    stem = os.path.basename(path)
    candidates = []
    for suf in BACKUP_SUFFIXES:
        candidates += glob.glob(os.path.join(directory, stem + suf + "*"))
        candidates += glob.glob(os.path.join(directory, "*" + suf, stem))
    candidates += glob.glob(os.path.join(directory, "backups", stem + "*"))
    best = None
    for c in candidates:
        try:
            mt = os.path.getmtime(c)
        except OSError:
            continue
        if best is None or mt > best[1]:
            best = (c, mt)
    return best


def run():
    lessons = get_lessons(NAME)
    now = time.time()
    findings = []
    for path in CRITICAL:
        try:
            st = os.stat(path)
            age_days = (now - st.st_mtime) / 86400
            entry = {"file": path, "exists": True,
                     "size": st.st_size, "age_days": round(age_days, 1),
                     "backup": None, "backup_age_days": None, "ok": False}
            found = _find_backup(path)
            if found:
                entry["backup"] = found[0]
                entry["backup_age_days"] = round((now - found[1]) / 86400, 1)
                entry["ok"] = entry["backup_age_days"] <= STALE_DAYS
                entry["detail"] = (
                    f"backup {os.path.basename(found[0])} is "
                    f"{entry['backup_age_days']}d old"
                    + ("" if entry["ok"] else f" - STALE (over {STALE_DAYS}d)"))
            else:
                entry["detail"] = "NO backup copy found"
            findings.append(entry)
        except OSError:
            findings.append({"file": path, "exists": False, "ok": False,
                             "detail": "critical file MISSING"})

    bad = [f for f in findings if not f.get("ok")]
    run_id = log_run(NAME, f"check backups for {len(CRITICAL)} files",
                     f"{len(findings) - len(bad)}/{len(findings)} protected")
    proposed = []
    for f in bad:
        proposed.append({
            "title": f"Backup Guard: {os.path.basename(f['file'])} unprotected",
            "kind": "ops",
            "detail": f"{f['file']}\n{f['detail']}\n"
                      "(Approve = Cyrus creates/refreshes a backup copy)",
        })
    return {
        "ok": not bad,
        "summary": f"{len(findings) - len(bad)}/{len(findings)} critical files have fresh backups",
        "details": {"findings": findings, "run_id": run_id,
                    "lessons_seen": lessons["outcomes_seen"]},
        "proposed_approvals": proposed,
    }

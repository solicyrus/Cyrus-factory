"""Knowledge Freshness — finds time-sensitive claims that may be stale.

Deterministic checker (no LLM needed), read-only. Reads the staged
AI-only knowledge file and lists markers that go stale with time:
year mentions (e.g. 2027), "Christmas", seasonal phrases, "coming soon",
"new"/"just opened" claims. If the staged file is missing it says so
honestly instead of guessing. Findings go to the approval queue so the
Monday knowledge merge can refresh them.
"""
import os
import re

from agents.learn import get_lessons, log_run

NAME = "knowledge_freshness"
KNOWLEDGE_FILE = os.path.expanduser(
    "~/workspace/your_files/knowledge-update/victoria-knowledge.txt")

PATTERNS = [
    ("year_mention", r"\b(202[4-9]|203\d)\b"),
    ("christmas", r"[Cc]hristmas"),
    ("seasonal", r"\b(summer|winter|spring|fall|autumn)\s+(202[4-9]|festival|season)\b"),
    ("coming_soon", r"coming soon|opening soon|will open|planned for"),
    ("new_claim", r"\bjust opened\b|\bnewly\b|\bbrand new\b"),
]


def run():
    lessons = get_lessons(NAME)
    try:
        with open(KNOWLEDGE_FILE, encoding="utf-8") as f:
            lines = f.read().splitlines()
    except FileNotFoundError:
        run_id = log_run(NAME, "read staged knowledge file", "MISSING - reported honestly")
        return {
            "ok": False,
            "summary": "Staged knowledge file is missing - nothing checked",
            "details": {"path": KNOWLEDGE_FILE, "run_id": run_id,
                        "lessons_seen": lessons["outcomes_seen"]},
            "proposed_approvals": [{
                "title": "Staged knowledge file missing",
                "kind": "ops",
                "detail": f"Expected at {KNOWLEDGE_FILE}. "
                          "The Monday merge needs this file.",
            }],
        }
    except OSError as e:
        run_id = log_run(NAME, "read staged knowledge file", f"unreadable: {e}")
        return {
            "ok": False,
            "summary": f"Knowledge file unreadable: {e}",
            "details": {"path": KNOWLEDGE_FILE, "run_id": run_id,
                        "lessons_seen": lessons["outcomes_seen"]},
            "proposed_approvals": [],
        }

    findings = []
    for i, line in enumerate(lines, 1):
        for label, pat in PATTERNS:
            for m in re.finditer(pat, line):
                findings.append({
                    "line": i, "marker": label,
                    "match": m.group(0),
                    "context": line.strip()[:120],
                })

    run_id = log_run(NAME, f"scan {len(lines)} lines for stale markers",
                     f"{len(findings)} time-sensitive markers found")
    proposed = []
    if findings:
        by_marker = {}
        for fnd in findings:
            by_marker.setdefault(fnd["marker"], []).append(fnd)
        detail = "\n".join(
            f"- {label}: {len(items)} (e.g. line {items[0]['line']}: "
            f"\"{items[0]['context'][:80]}\")"
            for label, items in sorted(by_marker.items()))
        proposed.append({
            "title": f"Knowledge Freshness: {len(findings)} time-sensitive markers to review",
            "kind": "quality",
            "detail": "Review before the Monday merge:\n" + detail,
        })
    return {
        "ok": True,
        "summary": f"{len(findings)} time-sensitive markers in {len(lines)} lines",
        "details": {"findings": findings[:50], "total": len(findings),
                    "run_id": run_id, "lessons_seen": lessons["outcomes_seen"]},
        "proposed_approvals": proposed,
    }

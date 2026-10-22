"""Factory HQ shared learning module (v2.0).

Every agent keeps a JSONL memory file at memory/<agent>.jsonl. Two entry
kinds:
  run      - logged by the agent itself at the end of run()
  outcome  - logged by the factory brain when Cyrus approves/rejects a
             draft that came from that run

get_lessons() reads the tail of the file and returns recent outcomes so the
next run can avoid what was rejected and repeat what was approved.
Standard library only.
"""
import json
import os
import time
import uuid

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEMORY_DIR = os.path.join(BASE, "memory")


def _path(agent):
    safe = "".join(c for c in str(agent) if c.isalnum() or c in "-_")
    return os.path.join(MEMORY_DIR, f"{safe or 'unknown'}.jsonl")


def _append(agent, entry):
    os.makedirs(MEMORY_DIR, exist_ok=True)
    entry["t"] = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
    with open(_path(agent), "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def log_run(agent, input_summary, output_summary):
    """Log one agent execution. Returns the run_id for approval linking."""
    run_id = uuid.uuid4().hex[:8]
    _append(agent, {
        "type": "run",
        "run_id": run_id,
        "input": str(input_summary)[:400],
        "output": str(output_summary)[:400],
    })
    return run_id


def log_outcome(agent, run_id, approved, note=""):
    """Log Cyrus's approve/reject decision on a draft from run_id."""
    _append(agent or "unknown", {
        "type": "outcome",
        "run_id": run_id,
        "approved": bool(approved),
        "note": str(note or "")[:400],
    })


def get_lessons(agent, n=5):
    """Recent outcomes for agent: counts + recent list + rejected outputs/notes."""
    entries = []
    try:
        with open(_path(agent), encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except FileNotFoundError:
        pass

    runs = {}
    for e in entries:
        if e.get("type") == "run" and e.get("run_id"):
            runs[e["run_id"]] = e.get("output", "")

    outcomes = [e for e in entries if e.get("type") == "outcome"][-n:]
    recent = []
    for o in outcomes:
        recent.append({
            "approved": o.get("approved"),
            "note": o.get("note", ""),
            "run_id": o.get("run_id"),
            "output": runs.get(o.get("run_id"), ""),
            "t": o.get("t", ""),
        })
    approved = sum(1 for o in recent if o.get("approved"))
    return {
        "agent": agent,
        "runs_total": sum(1 for e in entries if e.get("type") == "run"),
        "outcomes_seen": len(recent),
        "approved": approved,
        "rejected": len(recent) - approved,
        "recent": recent,
        "rejected_outputs": [r["output"] for r in recent
                             if not r["approved"] and r["output"]],
        "rejected_notes": [r["note"] for r in recent
                           if not r["approved"] and r["note"]],
    }

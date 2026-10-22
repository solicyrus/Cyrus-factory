"""CYRUS TEAM — Factory HQ brain.

A small, honest agent factory: a registry of REAL agents (Python modules
that do actual work), departments, a human-in-the-loop approval queue, and
an activity log. Nothing is fake — an agent is only listed if its run()
does something verifiable.

Run:  ./venv/bin/python app.py   ->  http://localhost:5050
"""
import importlib
import json
import os
import time
from datetime import datetime, timezone

from flask import Flask, jsonify, request, render_template

BASE = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(BASE, "factory_state.json")

app = Flask(__name__)

AGENT_MODULES = {
    "bug_hunter": "agents.bug_hunter",
    "content_writer": "agents.content_writer",
    "knowledge_improver": "agents.knowledge_improver",
}


def seed_state():
    return {
        "factory": "CYRUS TEAM - Factory HQ",
        "version": "v1.0",
        "mode": "human-in-the-loop",
        "departments": {
            "ENGINEERING": {"agents": ["bug_hunter"]},
            "CONTENT": {"agents": ["content_writer"]},
            "BRAIN": {"agents": ["knowledge_improver"]},
        },
        "agents": {
            "bug_hunter": {
                "name": "Bug Hunter",
                "department": "ENGINEERING",
                "description": "Live health checks: app homepage, sw.js version, main site, knowledge file sections.",
                "status": "idle", "last_run": None, "last_result": None,
            },
            "content_writer": {
                "name": "Content Writer",
                "department": "CONTENT",
                "description": "Drafts YouTube Shorts title/description/hashtags packs for approval.",
                "status": "idle", "last_run": None, "last_result": None,
            },
            "knowledge_improver": {
                "name": "Knowledge Improver",
                "department": "BRAIN",
                "description": "Inspects the staged knowledge file: sections A-N, Section N hard-rule keywords.",
                "status": "idle", "last_run": None, "last_result": None,
            },
        },
        "approvals": [
            {
                "id": "ap-zoom-001",
                "title": "iPhone zoom fix: #vta-chat-in 14px -> 16px (line 58, vta-chat-widget-premium.js)",
                "kind": "bugfix",
                "detail": "Real open bug from 2026-10-20/21 checks. Approve = include in the next widget upload.",
                "status": "pending",
                "created": "2026-10-21",
            }
        ],
        "activity": [],
        "next_approval_id": 2,
    }


def load_state():
    if not os.path.exists(STATE_FILE):
        state = seed_state()
        save_state(state)
        return state
    with open(STATE_FILE, encoding="utf-8") as f:
        return json.load(f)


def save_state(state):
    tmp = STATE_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
    os.replace(tmp, STATE_FILE)


def log(state, actor, text):
    state["activity"].insert(0, {
        "t": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "actor": actor,
        "text": text,
    })
    state["activity"] = state["activity"][:100]


@app.get("/")
def index():
    return render_template("dashboard.html")


@app.get("/api/status")
def api_status():
    s = load_state()
    return jsonify({
        "factory": s["factory"],
        "version": s["version"],
        "mode": s["mode"],
        "agents_active": len(s["agents"]),
        "departments": {k: len(v["agents"]) for k, v in s["departments"].items()},
        "approvals_pending": sum(1 for a in s["approvals"] if a["status"] == "pending"),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


@app.get("/api/agents")
def api_agents():
    return jsonify(load_state()["agents"])


@app.post("/api/run/<agent_id>")
def api_run(agent_id):
    s = load_state()
    if agent_id not in s["agents"] or agent_id not in AGENT_MODULES:
        return jsonify({"error": "unknown agent"}), 404
    agent = s["agents"][agent_id]
    agent["status"] = "running"
    save_state(s)
    try:
        mod = importlib.import_module(AGENT_MODULES[agent_id])
        kwargs = {}
        if agent_id == "content_writer":
            data = request.get_json(silent=True) or {}
            kwargs["topic"] = data.get("topic", "hidden gem in Victoria BC")
        result = mod.run(**kwargs)
    except Exception as e:  # never let an agent crash the factory
        result = {"ok": False, "summary": f"agent crashed: {e}",
                  "details": {}, "proposed_approvals": []}
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    agent["status"] = "idle"
    agent["last_run"] = now
    agent["last_result"] = result.get("summary")
    for p in result.get("proposed_approvals", []):
        aid = f"ap-{s['next_approval_id']:03d}"
        s["next_approval_id"] += 1
        s["approvals"].insert(0, {
            "id": aid, "title": p["title"], "kind": p.get("kind", "general"),
            "detail": p.get("detail", ""), "status": "pending", "created": now,
        })
    log(s, agent["name"], f"run finished: {result.get('summary')}")
    save_state(s)
    return jsonify({"agent": agent_id, "result": result})


@app.get("/api/approvals")
def api_approvals():
    return jsonify(load_state()["approvals"])


@app.post("/api/approvals/<aid>/<action>")
def api_approval_action(aid, action):
    if action not in ("approve", "reject"):
        return jsonify({"error": "action must be approve or reject"}), 400
    s = load_state()
    for a in s["approvals"]:
        if a["id"] == aid:
            if a["status"] != "pending":
                return jsonify({"error": "already decided"}), 400
            a["status"] = "approved" if action == "approve" else "rejected"
            a["decided"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            log(s, "Cyrus (HQ)", f"{action}d: {a['title'][:70]}")
            save_state(s)
            return jsonify({"ok": True, "id": aid, "status": a["status"]})
    return jsonify({"error": "not found"}), 404


@app.get("/api/activity")
def api_activity():
    return jsonify(load_state()["activity"])


if __name__ == "__main__":
    print("CYRUS TEAM - Factory HQ on http://localhost:5050")
    app.run(host="127.0.0.1", port=5050, debug=False)

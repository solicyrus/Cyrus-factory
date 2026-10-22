"""CYRUS TEAM — Factory HQ brain v2.1.

A small, honest agent factory: a registry of REAL agents (Python modules
that do actual work), departments, a human-in-the-loop approval queue, and
an activity log. v2.1: 30 real agents. v2.0 added the LEARNING LOOP: every agent reads its past
outcomes before running (agents/learn.py), and every approve/reject teaches
the agent that produced the draft. Creative agents can also use a shared
LLM backend (agents/llm.py) when API keys are set - otherwise they fall
back to deterministic rule-based mode.

Run:  ./venv/bin/python app.py   ->  http://localhost:5050
"""
import importlib
import json
import os
from datetime import datetime, timezone

from flask import Flask, jsonify, request, render_template

from agents import learn

BASE = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(BASE, "factory_state.json")
VERSION = "v2.1"

app = Flask(__name__)

AGENT_MODULES = {
    "bug_hunter": "agents.bug_hunter",
    "content_writer": "agents.content_writer",
    "knowledge_improver": "agents.knowledge_improver",
    "idea_maker": "agents.idea_maker",
    "support_tone": "agents.support_tone",
    "market_analyst": "agents.market_analyst",
    "market_scan": "agents.market_scan",
    "translator_check": "agents.translator_check",
    "ads_angles": "agents.ads_angles",
    "deploy_checker": "agents.deploy_checker",
    "shorts_planner": "agents.shorts_planner",
    "inbox_triage": "agents.inbox_triage",
    "qa_tester": "agents.qa_tester",
    "review_watcher": "agents.review_watcher",
    "pricing_guard": "agents.pricing_guard",
    "seo_writer": "agents.seo_writer",
    "competitor_watch": "agents.competitor_watch",
    "deadline_guard": "agents.deadline_guard",
    "testimonial_drafter": "agents.testimonial_drafter",
    "faq_builder": "agents.faq_builder",
    "nightly_reporter": "agents.nightly_reporter",
    "uptime_monitor": "agents.uptime_monitor",
    "knowledge_freshness": "agents.knowledge_freshness",
    "itinerary_checker": "agents.itinerary_checker",
    "social_caption": "agents.social_caption",
    "email_composer": "agents.email_composer",
    "backup_guard": "agents.backup_guard",
    "goal_tracker": "agents.goal_tracker",
    "review_responder": "agents.review_responder",
    "whatsapp_drafter": "agents.whatsapp_drafter",
}

# Which JSON body keys each agent accepts on POST /api/run/<agent>
AGENT_PARAMS = {
    "content_writer": ["topic"],
    "support_tone": ["message", "reply"],
    "market_analyst": ["text"],
    "qa_tester": ["text"],
    "pricing_guard": ["text"],
    "market_scan": ["symbols"],
    "seo_writer": ["topic"],
    "itinerary_checker": ["text"],
    "social_caption": ["topic"],
    "email_composer": ["to", "subject", "purpose"],
    "review_responder": ["reviewer_name", "rating", "text"],
    "whatsapp_drafter": ["topic"],
}

# (id, display name, department, description)
AGENT_DEFS = [
    ("bug_hunter", "Bug Hunter", "ENGINEERING",
     "Live health checks: app homepage, sw.js version, main site, knowledge file sections."),
    ("deploy_checker", "Deploy Checker", "OPS",
     "Live deploy checks: app, main site, USA subdomain, service worker."),
    ("knowledge_improver", "Knowledge Improver", "BRAIN",
     "Inspects the staged knowledge file: sections A-N, Section N hard-rule keywords."),
    ("qa_tester", "QA Tester", "QUALITY",
     "5 hardcoded honesty trap checks on any text (prices, phones, visa claims)."),
    ("translator_check", "Translator Check", "QUALITY",
     "Verifies the 6-language closing lines: presence, formality, price in knowledge."),
    ("pricing_guard", "Pricing Guard", "QUALITY",
     "Scans text for any price and checks it against the real prices.json catalog."),
    ("content_writer", "Content Writer", "CONTENT",
     "Drafts YouTube Shorts title/description/hashtags packs for approval."),
    ("shorts_planner", "Shorts Planner", "CONTENT",
     "Builds a 1-week Shorts calendar (Sat/Mon/Wed slots) with title ideas."),
    ("seo_writer", "SEO Writer", "CONTENT",
     "Drafts an SEO article outline (title, headings, CTA) for a topic."),
    ("idea_maker", "Idea Maker", "IDEAS",
     "Generates 3 concrete business ideas for the tour business."),
    ("support_tone", "Support Tone", "SUPPORT",
     "Checks a customer reply against tone rules: honest, short, no fake promises."),
    ("faq_builder", "FAQ Builder", "SUPPORT",
     "Drafts 3 FAQ entries with honest short answers for Cyrus AI."),
    ("market_analyst", "Market Analyst", "MARKET",
     "Flags price inconsistencies in text against the real prices catalog."),
    ("market_scan", "Market Scan", "MARKET",
     "Live market data (BTC, ETH, USD/CAD) from Yahoo Finance; flags big 24h moves."),
    ("review_watcher", "Review Watcher", "MARKET",
     "Flags negative/urgent reviews needing a reply, with a reply template."),
    ("competitor_watch", "Competitor Watch", "MARKET",
     "HTTP-checks competitor sites for downtime or status changes."),
    ("ads_angles", "Ads Angles", "MARKETING",
     "Drafts 3 honest ad angles for Cyrus AI."),
    ("testimonial_drafter", "Testimonial Drafter", "MARKETING",
     "Drafts a short, polite review-request message."),
    ("inbox_triage", "Inbox Triage", "OPS",
     "Classifies inbox items: urgent / can-wait / ignore."),
    ("deadline_guard", "Deadline Guard", "OPS",
     "Lists business deadlines within 30 days; urgent ones within 7."),
    ("nightly_reporter", "Nightly Reporter", "OPS",
     "Composes the nightly Persian business summary draft from the activity log."),
    ("uptime_monitor", "Uptime Monitor", "OPS",
     "Timed health checks with a persistent log; flags downtime and slow responses."),
    ("email_composer", "Email Composer", "OPS",
     "Drafts a short professional business email (draft only, never sends)."),
    ("backup_guard", "Backup Guard", "OPS",
     "Verifies backup copies exist for critical files; flags missing or stale ones."),
    ("goal_tracker", "Goal Tracker", "OPS",
     "Tracks Cyrus's real business goals: overdue, due soon, upcoming."),
    ("knowledge_freshness", "Knowledge Freshness", "BRAIN",
     "Finds time-sensitive claims in the staged knowledge file that may be stale."),
    ("itinerary_checker", "Itinerary Checker", "QUALITY",
     "Validates an itinerary: invented prices, phone numbers, visa promises, day counts."),
    ("social_caption", "Social Caption", "CONTENT",
     "Drafts an Instagram caption + hashtags (honest, no fake claims)."),
    ("review_responder", "Review Responder", "SUPPORT",
     "Drafts a short honest reply to a customer review."),
    ("whatsapp_drafter", "WhatsApp Drafter", "MARKETING",
     "Drafts a short WhatsApp broadcast with a Cyrus AI CTA (draft only)."),
]


def seed_state():
    departments = {}
    agents = {}
    for aid, name, dept, desc in AGENT_DEFS:
        departments.setdefault(dept, {"agents": []})["agents"].append(aid)
        agents[aid] = {
            "name": name, "department": dept, "description": desc,
            "status": "idle", "last_run": None, "last_result": None,
        }
    return {
        "factory": "CYRUS TEAM - Factory HQ",
        "version": VERSION,
        "mode": "human-in-the-loop",
        "departments": departments,
        "agents": agents,
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


def _migrate(state):
    """Upgrade an older state file to the current version without losing
    approvals, activity or decisions."""
    if state.get("version") == VERSION:
        return state
    seed = seed_state()
    for dept, dinfo in seed["departments"].items():
        if dept not in state["departments"]:
            state["departments"][dept] = dinfo
        else:
            for aid in dinfo["agents"]:
                if aid not in state["departments"][dept]["agents"]:
                    state["departments"][dept]["agents"].append(aid)
    for aid, ainfo in seed["agents"].items():
        if aid not in state["agents"]:
            state["agents"][aid] = ainfo
    state["version"] = VERSION
    return state


def load_state():
    if not os.path.exists(STATE_FILE):
        state = seed_state()
        save_state(state)
        return state
    with open(STATE_FILE, encoding="utf-8") as f:
        state = json.load(f)
    if state.get("version") != VERSION:
        state = _migrate(state)
        save_state(state)
    return state


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
        data = request.get_json(silent=True) or {}
        kwargs = {k: data[k] for k in AGENT_PARAMS.get(agent_id, []) if k in data}
        result = mod.run(**kwargs)
    except Exception as e:  # never let an agent crash the factory
        result = {"ok": False, "summary": f"agent crashed: {e}",
                  "details": {}, "proposed_approvals": []}
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    agent["status"] = "idle"
    agent["last_run"] = now
    agent["last_result"] = result.get("summary")
    # The agent logs its own run via agents/learn.py and returns the run_id
    # in details; fall back to logging here if it didn't.
    run_id = (result.get("details") or {}).get("run_id")
    if not run_id:
        try:
            run_id = learn.log_run(agent_id, json.dumps(kwargs)[:200] or "manual run",
                                   result.get("summary", ""))
        except Exception:
            run_id = None
    for p in result.get("proposed_approvals", []):
        aid = f"ap-{s['next_approval_id']:03d}"
        s["next_approval_id"] += 1
        s["approvals"].insert(0, {
            "id": aid, "title": p["title"], "kind": p.get("kind", "general"),
            "detail": p.get("detail", ""), "status": "pending", "created": now,
            "agent": agent_id, "run_id": run_id,
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
            data = request.get_json(silent=True) or {}
            note = str(data.get("note", ""))[:400]
            a["status"] = "approved" if action == "approve" else "rejected"
            a["decided"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            if note:
                a["note"] = note
            log(s, "Cyrus (HQ)", f"{action}d: {a['title'][:70]}")
            # THE LEARNING LOOP: teach the originating agent what happened.
            # Never let a learning failure break the approval itself.
            try:
                learn.log_outcome(a.get("agent") or "hq", a.get("run_id"),
                                  action == "approve", note)
            except Exception:
                pass
            save_state(s)
            return jsonify({"ok": True, "id": aid, "status": a["status"]})
    return jsonify({"error": "not found"}), 404


@app.get("/api/activity")
def api_activity():
    return jsonify(load_state()["activity"])


if __name__ == "__main__":
    print("CYRUS TEAM - Factory HQ v2.1 on http://localhost:5050")
    app.run(host="127.0.0.1", port=5050, debug=False)

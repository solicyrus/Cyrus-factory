"""Market Scan — live market data agent (salvaged from the old Cyrus-team project).

The old Meta-AI project had exactly one genuinely working piece: a live
market scan (yfinance). This agent is its honest rebuild: stdlib only,
no API keys, real numbers from Yahoo Finance chart API.

Deterministic checker (no LLM needed). Symbols default to BTC-USD,
ETH-USD and CAD=X (USD/CAD matters for his CAD pricing).
"""
import json
import urllib.request

from agents.learn import get_lessons, log_run

NAME = "market_scan"
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}

DEFAULT_SYMBOLS = ["BTC-USD", "ETH-USD", "CAD=X"]


def _fetch(symbol):
    url = (f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
           f"?interval=1d&range=5d")
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=15) as r:
        data = json.loads(r.read().decode())
    result = (data.get("chart") or {}).get("result") or []
    if not result:
        raise ValueError("empty chart result")
    closes = (result[0].get("indicators") or {}).get("quote", [{}])[0].get("close") or []
    closes = [c for c in closes if c]
    if len(closes) < 2:
        raise ValueError("not enough closes")
    last, prev = closes[-1], closes[-2]
    return {
        "symbol": symbol,
        "price": round(last, 4),
        "change_24h_pct": round((last / prev - 1) * 100, 2),
    }


def run(symbols=None):
    lessons = get_lessons(NAME)
    syms = symbols or DEFAULT_SYMBOLS
    if isinstance(syms, str):
        syms = [s.strip() for s in syms.split(",") if s.strip()]

    scanned, errors = [], []
    for s in syms[:8]:
        try:
            scanned.append(_fetch(s))
        except Exception as e:  # noqa: BLE001 - report honestly per symbol
            errors.append({"symbol": s, "error": str(e)[:120]})

    movers = sorted(scanned, key=lambda x: abs(x["change_24h_pct"]), reverse=True)
    summary = "; ".join(
        f"{m['symbol']} {m['price']} ({m['change_24h_pct']:+.2f}%)" for m in movers
    ) or "no data"
    if errors:
        summary += f" | {len(errors)} symbol(s) failed"

    run_id = log_run(NAME, f"scan {len(syms)} symbols",
                     f"{len(scanned)} ok, {len(errors)} failed: {summary[:200]}")

    proposed = []
    for m in movers:
        if abs(m["change_24h_pct"]) >= 5:
            proposed.append({
                "title": f"Big move: {m['symbol']} {m['change_24h_pct']:+.2f}% in 24h",
                "kind": "market",
                "detail": (f"{m['symbol']} is at {m['price']} "
                           f"({m['change_24h_pct']:+.2f}% vs yesterday)."),
            })

    return {
        "ok": True,
        "summary": summary,
        "details": {"scanned": scanned, "errors": errors, "run_id": run_id,
                    "lessons_seen": lessons["outcomes_seen"]},
        "proposed_approvals": proposed,
    }

"""
wind_closure.py — Real Wind MCP verification closure (NEXT_PHASE Loop 6).

For a small set of clearly-defined monthly series, query Wind MCP with the
PRECISE indicator name (not the iFind hierarchical path, which fuzzy-matches
to wrong indicators), validate against the DB's last two actual observations,
and mark wind_verified=true with the real Wind code + name on success.

Closure series (USD-denominated, divide_1e8 in DB, clear concept):
  fx_fwd:B   中国:银行自身结汇金额:当月值          [M5207846]
  fx_fwd:C   中国:银行自身售汇金额:当月值          [M5207848]
  fx_fwd:F   中国:银行代客远期售汇签约额:当月值     (resolve)
  fx_cspot:H 中国:银行代客结汇:证券投资:当月值      (resolve)
  fx_cspot:O 中国:银行代客售汇:证券投资:当月值      (resolve)

The Wind query returns 亿美元 already, so DB values (also 亿美元) compare with
identity transform here (DB raw is stored post-divide_1e8 == 亿).
"""
import sys, json, subprocess, os, sqlite3
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parent))
from wind_mcp_adapter import SKILL_DIR, WIND_CLI

DB_PATH = "data/monthly_brief.sqlite"
MAPPING_PATH = "config/wind_mapping.json"

# series_id -> precise Wind indicator query (name that resolves to the right EDB code)
CLOSURE = {
    "fx_fwd:B": "中国:银行自身结汇金额:当月值",
    "fx_fwd:C": "中国:银行自身售汇金额:当月值",
    "fx_fwd:F": "中国:银行代客远期售汇签约额:当月值",
    "fx_cspot:H": "中国:银行代客结汇:证券投资:当月值",
    "fx_cspot:O": "中国:银行代客售汇金额:证券投资:当月值",
}

OVERLAP_TOL = 0.01  # 1% relative — Wind vs DB rounding


def wind_query(indicator, begin, end):
    """Query Wind MCP; return list of (indicator_obj) candidates with date map."""
    params = json.dumps({
        "metricIdsStr": indicator, "beginDate": begin, "endDate": end,
        "freq": "月", "magnitude": "亿", "currency": "USD"
    })
    try:
        r = subprocess.run(["node", WIND_CLI, "call", "economic_data",
                            "get_economic_data", params],
                           capture_output=True, text=True, timeout=90, cwd=SKILL_DIR)
    except Exception as e:
        return None
    if r.returncode != 0 or not r.stdout.strip():
        return None
    try:
        d = json.loads(r.stdout)
        text = d.get("content", [{}])[0].get("text", "")
        p = json.loads(text)
    except (json.JSONDecodeError, IndexError):
        return None
    dates = p.get("data", {}).get("date", [])
    out = []
    for ind in p.get("data", {}).get("indicatorInfo", []):
        dmap = {}
        for dt, v in zip(dates, ind.get("data", [])):
            if v is not None:
                ds = f"{str(dt)[:4]}-{str(dt)[4:6]}-{str(dt)[6:8]}"
                dmap[ds] = float(v)
        out.append({"code": ind.get("code"), "name": ind.get("name", ""),
                    "unit": ind.get("unit", ""), "data": dmap})
    return out


def pick_exact(candidates):
    """Pick the national '当月值' indicator (中国: prefix, no 人民币/累计/province)."""
    for c in candidates:
        n = c["name"]
        if n.startswith("中国:") and "当月值" in n and "人民币" not in n and "累计" not in n:
            return c
    return None


def get_db_last_two(conn, sid):
    rows = conn.execute(
        "SELECT date, value FROM observations WHERE series_id=? AND value IS NOT NULL "
        "ORDER BY date DESC LIMIT 2", (sid,)).fetchall()
    if len(rows) < 2:
        return None
    return {r[0][:10]: r[1] for r in rows}


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    mappings = json.load(open(MAPPING_PATH, encoding="utf-8"))
    by_id = {m["series_id"]: m for m in mappings if isinstance(m, dict) and "series_id" in m}

    verified, failed = [], []
    audit = []

    for sid, query in CLOSURE.items():
        db_map = get_db_last_two(conn, sid)
        if not db_map:
            failed.append((sid, "no 2 DB points")); continue
        dates = sorted(db_map.keys())
        begin = dates[0].replace("-", "")
        end = dates[-1].replace("-", "")

        cands = wind_query(query, begin, end)
        if not cands:
            failed.append((sid, "Wind query returned nothing")); continue
        match = pick_exact(cands)
        if not match:
            failed.append((sid, f"no exact indicator among {len(cands)} candidates")); continue

        # Two-point overlap check
        overlap = sorted(set(db_map) & set(match["data"]))
        if len(overlap) < 2:
            failed.append((sid, f"only {len(overlap)} overlap points")); continue
        errs = []
        for d in overlap:
            dv, wv = db_map[d], match["data"][d]
            rel = abs(wv - dv) / abs(dv) if abs(dv) > 1e-9 else abs(wv - dv)
            errs.append((d, dv, wv, rel))
        max_rel = max(e[3] for e in errs)

        rec = {"series_id": sid, "query": query, "wind_code": match["code"],
               "wind_name": match["name"], "wind_unit": match["unit"],
               "overlap": len(overlap), "max_rel_err": round(max_rel, 5),
               "samples": [(d, round(dv, 4), round(wv, 4)) for d, dv, wv, _ in errs]}
        audit.append(rec)

        if max_rel <= OVERLAP_TOL:
            # Mark wind_verified=true on the mapping
            m = by_id[sid]
            m["wind_verified"] = True
            m["wind_code"] = match["code"]
            m["wind_name"] = match["name"]
            m["wind_query_exact"] = query
            m["wind_verified_at"] = "2026-06-23"
            m["wind_verification_note"] = (
                f"Real Wind MCP closure: {match['code']} {match['name']}, "
                f"{len(overlap)} overlap pts, max_rel={max_rel:.4%}")
            verified.append(sid)
            print(f"  ✅ {sid}: {match['code']} {match['name']} "
                  f"({len(overlap)} pts, max_rel={max_rel:.4%})")
        else:
            failed.append((sid, f"overlap mismatch max_rel={max_rel:.2%}"))
            print(f"  ❌ {sid}: max_rel={max_rel:.2%} > {OVERLAP_TOL:.0%}")

    # Persist mapping updates
    if verified:
        json.dump(mappings, open(MAPPING_PATH, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=2)

    # Save audit
    os.makedirs("data", exist_ok=True)
    json.dump({"verified": verified, "failed": failed, "audit": audit,
               "closed_at": "2026-06-23"},
              open("data/wind_closure_audit.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)

    print(f"\n=== Wind closure: {len(verified)} verified, {len(failed)} failed ===")
    for sid, reason in failed:
        print(f"  ✗ {sid}: {reason}")
    conn.close()
    return len(verified)


if __name__ == "__main__":
    main()

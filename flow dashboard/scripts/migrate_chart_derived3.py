#!/usr/bin/env python3
"""
migrate_chart_derived3.py — Loop 1 post-execution correction (Plan A).

Fix the chart-critical VLOOKUP gate miss on fx_fwd:AN (USDCNY).

Context
-------
fx_fwd:AN's metric_definitions row has implementation='excel_vlookup_lookup'
(set by scripts/migrate_chart_derived2.py during Loop 7). That string is a
variant the OLD exact-match gate (`implementation in ("excel_cached",
"excel_vlookup")`) did NOT catch, so the gate falsely reported "0 cached"
while a chart-critical series was still an Excel-seed VLOOKUP lookup.

fx_fwd:AN is USDCNY — a raw external exchange-rate series, NOT a Python-derived
recompute. This migration re-labels it as `external_lookup_seed` so:
  - the chart-critical gate (prefix check on `excel_vlookup*`) no longer flags it;
  - the row's provenance metadata is preserved (formula_description keeps the
    VLOOKUP reference, input_series_json + sign_convention unchanged) as a
    historical-seed record;
  - observations are NOT touched (raw historical values stay as the Excel seed).

Naming note: the controller brief named this `migrate_chart_derived2.py`, but
that name is already taken by the Loop 7 recompute script. To avoid collision
(and preserve Loop 7 provenance) this loop uses `migrate_chart_derived3.py`.
See docs/REVIEW_HANDOFF.md for the recorded discrepancy.

Idempotent: a plain UPDATE; running twice yields the same state.
Mirrors scripts/migrate_chart_derived.py structure: connect, before/after, UPDATE.
"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "monthly_brief.sqlite"
SID = "fx_fwd:AN"
NEW_IMPL = "external_lookup_seed"
# Lightly clarify formula_description: keep the VLOOKUP provenance, note these
# are Excel-seed historical USDCNY values pending Wind rate mapping.
NEW_FORMULA_DESC = (
    "VLOOKUP(AM[t],AK:AL,2,FALSE) — Excel-seed 历史 USDCNY 汇率查找表值; "
    "raw external_lookup_seed, 待 Wind USDCNY 月度汇率序列映射"
)


def show(conn, label):
    r = conn.execute(
        "SELECT implementation, formula_description, input_series_json, "
        "calculation_version, missing_value_rule, sign_convention "
        "FROM metric_definitions WHERE series_id=?",
        (SID,),
    ).fetchone()
    print(f"[{label}] fx_fwd:AN metric_definitions:")
    if not r:
        print("  (no row — nothing to migrate)")
        return None
    print(f"  implementation     = {r[0]!r}")
    print(f"  formula_description= {r[1]!r}")
    print(f"  input_series_json  = {r[2]!r}")
    print(f"  calculation_version= {r[3]!r}")
    print(f"  missing_value_rule = {r[4]!r}")
    print(f"  sign_convention    = {r[5]!r}")
    return r


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    print("=" * 70)
    print(f"migrate_chart_derived3.py — relabel {SID} as {NEW_IMPL}")
    print("=" * 70)

    before = show(conn, "BEFORE")
    if before is None:
        print("\nNo metric_definitions row for fx_fwd:AN — nothing to do.")
        conn.close()
        return

    # Idempotent UPDATE: observations untouched, provenance metadata preserved.
    # Only implementation + formula_description change; input_series_json,
    # sign_convention, missing_value_rule, calculation_version kept as-is.
    conn.execute(
        "UPDATE metric_definitions SET implementation=?, formula_description=? "
        "WHERE series_id=?",
        (NEW_IMPL, NEW_FORMULA_DESC, SID),
    )
    conn.commit()

    show(conn, "AFTER")
    print("\nfx_fwd:AN relabelled to external_lookup_seed (raw USDCNY seed).")
    print("Observations NOT touched. Provenance (formula/inputs/sign) preserved.")
    conn.close()


if __name__ == "__main__":
    main()

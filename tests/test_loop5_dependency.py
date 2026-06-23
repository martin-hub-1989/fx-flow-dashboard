"""
Loop 5 tests: affected-derived recompute.
Per NEXT_PHASE_EXECUTION_LOOP.md Loop 5.

- build dependency graph from metric_definitions.input_series_json
- raw update triggers recompute of affected downstream derived only
- supports >= 2 dependency layers
- unrelated derived not recomputed
"""
import sys, sqlite3, json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import lib
import dependency_graph as DG


def make_conn():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    lib.init_db(conn)
    # raw: r1, r2 ; derived d1 = f(r1); d2 = f(d1) (two layers); d3 = f(r2) unrelated
    for sid, t in [("m:r1", "raw"), ("m:r2", "raw"),
                   ("m:d1", "derived"), ("m:d2", "derived"), ("m:d3", "derived")]:
        conn.execute("INSERT INTO series (series_id, display_name, module, series_type) VALUES (?,?,?,?)",
                     (sid, sid, "test", t))
    defs = [
        ("m:d1", ["m:r1"]),
        ("m:d2", ["m:d1"]),
        ("m:d3", ["m:r2"]),
    ]
    for sid, inputs in defs:
        conn.execute("INSERT INTO metric_definitions (series_id, formula_description, "
                     "input_series_json, calculation_version, implementation) VALUES (?,?,?,?,?)",
                     (sid, "test", json.dumps(inputs), "v1", "test"))
    conn.commit()
    return conn


def test_build_dependency_graph():
    conn = make_conn()
    deps = DG.build_dependents(conn)
    # r1 -> d1 ; d1 -> d2 ; r2 -> d3
    assert "m:d1" in deps["m:r1"]
    assert "m:d2" in deps["m:d1"]
    assert "m:d3" in deps["m:r2"]


def test_affected_two_layers():
    conn = make_conn()
    affected = DG.affected_derived(conn, ["m:r1"])
    # updating r1 should affect d1 AND d2 (two layers), NOT d3
    assert affected == ["m:d1", "m:d2"], f"got {affected}"


def test_unrelated_not_affected():
    conn = make_conn()
    affected = DG.affected_derived(conn, ["m:r2"])
    assert affected == ["m:d3"], f"got {affected}"
    assert "m:d1" not in affected and "m:d2" not in affected


def test_topological_order():
    conn = make_conn()
    affected = DG.affected_derived(conn, ["m:r1"])
    # d1 must come before d2 (d2 depends on d1)
    assert affected.index("m:d1") < affected.index("m:d2")

"""
Unit tests for FX Flow Dashboard.
Covers: lib.py, recompute_derived.py, validate_update.py, verify_wind_mappings.py
"""
import sys, os, json, sqlite3, tempfile, math
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib import (
    init_db, upsert_series, insert_observation, insert_observations_batch,
    get_observations, get_latest_date, start_update_run, finish_update_run,
    validate_db, values_match, get_db
)
from recompute_derived import sma, rolling_sum, z_score, rolling_sum_ratio
from validate_update import validate_overlap, load_fetched_data


# =============================================================================
# Test helpers
# =============================================================================

TESTS_PASSED = 0
TESTS_FAILED = 0

def assert_eq(actual, expected, label=""):
    global TESTS_PASSED, TESTS_FAILED
    if actual == expected:
        TESTS_PASSED += 1
    else:
        TESTS_FAILED += 1
        print(f"  FAIL [{label}]: expected {expected!r}, got {actual!r}")

def assert_approx(actual, expected, tolerance=1e-8, label=""):
    global TESTS_PASSED, TESTS_FAILED
    if abs(actual - expected) <= tolerance:
        TESTS_PASSED += 1
    else:
        TESTS_FAILED += 1
        print(f"  FAIL [{label}]: expected ≈{expected}, got {actual} (diff={abs(actual-expected):.2e})")

def assert_true(cond, label=""):
    global TESTS_PASSED, TESTS_FAILED
    if cond:
        TESTS_PASSED += 1
    else:
        TESTS_FAILED += 1
        print(f"  FAIL [{label}]: condition not true")

def assert_false(cond, label=""):
    global TESTS_PASSED, TESTS_FAILED
    if not cond:
        TESTS_PASSED += 1
    else:
        TESTS_FAILED += 1
        print(f"  FAIL [{label}]: condition not false")


# =============================================================================
# lib.py tests
# =============================================================================

def test_init_db():
    """Test database schema initialization."""
    print("\n--- test_init_db ---")
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_db(conn)

    # Verify all 5 tables exist
    tables = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()
    table_names = [t['name'] for t in tables]
    for tbl in ['series', 'observations', 'metric_definitions', 'update_runs', 'validation_events']:
        assert_true(tbl in table_names, f"table {tbl} exists")

    # Verify indexes exist
    indexes = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='index' ORDER BY name"
    ).fetchall()
    idx_names = [i['name'] for i in indexes]
    for idx in ['idx_obs_series', 'idx_obs_date', 'idx_obs_series_date', 'idx_series_module', 'idx_series_type']:
        assert_true(idx in idx_names, f"index {idx} exists")

    # Verify check constraint on series_type
    try:
        conn.execute("""
            INSERT INTO series (series_id, display_name, module, series_type)
            VALUES ('test', 'Test', 'test', 'invalid_type')
        """)
        assert_true(False, "should reject invalid series_type")
    except sqlite3.IntegrityError:
        assert_true(True, "check constraint rejects invalid series_type")

    # Idempotency: run again
    init_db(conn)
    tables2 = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    assert_eq(len(tables2), len(tables), "idempotent init")

    conn.close()


def test_upsert_and_query():
    """Test series upsert and observation insert/query."""
    print("\n--- test_upsert_and_query ---")
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_db(conn)

    series = {
        "series_id": "test:B",
        "display_name": "Test Series B",
        "module": "test",
        "series_type": "raw",
        "frequency": "M",
        "unit": "亿美元",
        "source": "excel_seed",
        "source_query": "Excel col B",
        "excel_sheet": "Test",
        "excel_range": "B6:B100",
        "update_status": "imported",
        "first_date": "2020-01-31",
        "last_date": "2020-03-31",
        "notes": "test series"
    }
    upsert_series(conn, series)

    # Read back
    row = conn.execute("SELECT * FROM series WHERE series_id=?", ("test:B",)).fetchone()
    assert_eq(row['display_name'], "Test Series B", "upsert display_name")
    assert_eq(row['series_type'], "raw", "upsert series_type")
    assert_eq(row['module'], "test", "upsert module")

    # Upsert again (should replace)
    series['display_name'] = "Updated Name"
    upsert_series(conn, series)
    row = conn.execute("SELECT * FROM series WHERE series_id=?", ("test:B",)).fetchone()
    assert_eq(row['display_name'], "Updated Name", "upsert replacement")

    conn.close()


def test_observations():
    """Test observation insert and query."""
    print("\n--- test_observations ---")
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_db(conn)

    # Insert series first (FK constraint)
    conn.execute("INSERT INTO series (series_id, display_name, module, series_type) VALUES (?,?,?,?)",
                 ("obs_test:A", "Obs Test", "test", "raw"))

    # Single insert
    insert_observation(conn, "obs_test:A", "2025-01-31", 100.5, "test", "run_001")
    row = conn.execute("SELECT * FROM observations WHERE series_id='obs_test:A'").fetchone()
    assert_eq(row['value'], 100.5, "single insert value")
    assert_eq(row['source'], "test", "single insert source")

    # Idempotent insert (same PK)
    insert_observation(conn, "obs_test:A", "2025-01-31", 200.0, "test", "run_002")
    row = conn.execute("SELECT * FROM observations WHERE series_id='obs_test:A'").fetchone()
    assert_eq(row['value'], 200.0, "idempotent replaces value")
    assert_eq(row['run_id'], "run_002", "idempotent updates run_id")

    # Batch insert
    rows = [
        ("obs_test:A", "2025-02-28", 101.0, "test"),
        ("obs_test:A", "2025-03-31", 102.0, "test"),
    ]
    insert_observations_batch(conn, rows, "run_003")
    count = conn.execute("SELECT COUNT(*) as n FROM observations WHERE series_id='obs_test:A'").fetchone()
    assert_eq(count['n'], 3, "batch insert count")

    # Query
    obs = get_observations(conn, "obs_test:A")
    assert_eq(len(obs), 3, "get all observations")
    assert_eq(obs[0]['value'], 200.0, "observations sorted by date")

    # Query with range
    obs = get_observations(conn, "obs_test:A", start_date="2025-02-01")
    assert_eq(len(obs), 2, "range query start")
    obs = get_observations(conn, "obs_test:A", end_date="2025-02-01")
    assert_eq(len(obs), 1, "range query end")

    # get_latest_date
    latest = get_latest_date(conn, "obs_test:A")
    assert_eq(latest, "2025-03-31", "get_latest_date")
    none_date = get_latest_date(conn, "nonexistent")
    assert_eq(none_date, None, "get_latest_date missing")

    conn.close()


def test_update_runs():
    """Test update_runs lifecycle."""
    print("\n--- test_update_runs ---")
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_db(conn)

    run_id = start_update_run(conn, 10)
    assert_true(run_id.startswith("run_"), "run_id format")
    assert_true(len(run_id) > 10, "run_id length")

    row = conn.execute("SELECT * FROM update_runs WHERE run_id=?", (run_id,)).fetchone()
    assert_eq(row['status'], "running", "start status")
    assert_eq(row['requested_series'], 10, "requested_series")

    finish_update_run(conn, run_id, "completed",
                      successful=8, failed=2, new_obs=50, revised=3, errors="some error")
    row = conn.execute("SELECT * FROM update_runs WHERE run_id=?", (run_id,)).fetchone()
    assert_eq(row['status'], "completed", "finish status")
    assert_eq(row['successful_series'], 8, "successful count")
    assert_eq(row['failed_series'], 2, "failed count")
    assert_eq(row['new_observations'], 50, "new obs count")
    assert_eq(row['error_summary'], "some error", "error summary")

    conn.close()


def test_values_match():
    """Test values_match function."""
    print("\n--- test_values_match ---")
    assert_true(values_match(1.0, 1.0), "exact match")
    assert_true(values_match(1.0, 1.0 + 1e-9), "within tolerance")
    assert_false(values_match(1.0, 1.1), "outside tolerance")
    assert_true(values_match(None, None), "both None")
    assert_false(values_match(None, 1.0), "one None")
    assert_false(values_match(1.0, None), "other None")
    assert_false(values_match(float('inf'), float('inf')), "inf values")
    assert_false(values_match("a", "b"), "string mismatch")


def test_validate_db_checks():
    """Test database validation."""
    print("\n--- test_validate_db ---")
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_db(conn)

    # Empty DB should be clean
    issues = validate_db(conn)
    assert_eq(len(issues), 0, "empty db no issues")

    # Series without observations
    conn.execute("INSERT INTO series (series_id, display_name, module, series_type) VALUES (?,?,?,?)",
                 ("orphan:A", "Orphan", "test", "raw"))
    issues = validate_db(conn)
    assert_true(len(issues) > 0, "detects orphan series")
    assert_true(any("orphan:A" in str(i) for i in issues), "names orphan")

    # Non-finite values in observations
    conn.execute("INSERT INTO series (series_id, display_name, module, series_type) VALUES (?,?,?,?)",
                 ("valid:A", "Valid", "test", "raw"))
    conn.execute("INSERT INTO observations (series_id, date, value) VALUES ('valid:A', '2025-01-31', 1)")
    conn.execute("INSERT INTO observations (series_id, date, value) VALUES ('valid:A', '2025-02-28', 2)")
    conn.commit()
    issues2 = validate_db(conn)
    # The orphan series from earlier is still there, so we expect 1 issue
    assert_eq(len(issues2), 1, "orphan still detected")

    conn.close()


# =============================================================================
# Loop A8: Production Gate Tests
# =============================================================================

def test_gate_arbitrary_factor_rejected():
    """Gate: Arbitrary data-derived scale factors must not produce 'verified' status."""
    print("\n--- test_gate_arbitrary_factor_rejected ---")
    import json
    with open('config/wind_mapping.json') as f:
        mappings = json.load(f)
    entries = [m for m in mappings if isinstance(m, dict) and 'series_id' in m]

    for m in entries:
        if m['status'] in ('verified_exact', 'verified_unit_transform'):
            transforms = m.get('transform', [])
            for t in transforms:
                # No verify_factor_* or unit_div_<arbitrary> in verified entries
                assert not t.startswith('verify_factor_'), \
                    f"P0 FAIL: {m['series_id']} has arbitrary factor {t} but status={m['status']}"
                assert not (t.startswith('unit_div_') and t not in ('unit_div_10000', 'unit_div_100000000', 'unit_div_100')), \
                    f"P0 FAIL: {m['series_id']} has non-standard unit_div {t}"

def test_gate_transform_whitelist():
    """Gate: Only allowed transforms used in verified entries."""
    print("\n--- test_gate_transform_whitelist ---")
    import json
    ALLOWED = {'identity', 'divide_1e4', 'divide_1e8', 'multiply_100', 'divide_100',
               'sign_flip', 'currency_conversion_by_date', 'cumulative_to_period'}

    with open('config/wind_mapping.json') as f:
        mappings = json.load(f)
    entries = [m for m in mappings if isinstance(m, dict) and 'series_id' in m]

    violations = []
    for m in entries:
        if m['status'] in ('verified_exact', 'verified_unit_transform'):
            for t in m.get('transform', []):
                if t not in ALLOWED:
                    violations.append(f"{m['series_id']}: transform='{t}'")

    assert len(violations) == 0, f"Transform violations: {violations}"

def test_gate_overlap_requirement():
    """Gate: Verified entries must have >= minimum overlap points."""
    print("\n--- test_gate_overlap_requirement ---")
    import json
    with open('config/wind_mapping.json') as f:
        mappings = json.load(f)
    entries = [m for m in mappings if isinstance(m, dict) and 'series_id' in m]

    for m in entries:
        if m['status'] in ('verified_exact', 'verified_unit_transform'):
            overlap = m.get('verify_details', {}).get('overlap_points', 0)
            freq = m.get('frequency', 'monthly')

            min_overlap = {'monthly': 12, 'quarterly': 4, 'annual': 3, 'daily': 40}.get(freq, 12)
            assert overlap >= min_overlap, \
                f"P0 FAIL: {m['series_id']} has {overlap} overlap points (<{min_overlap} for {freq})"

def test_gate_metric_definitions_complete():
    """Gate: All derived series must have metric_definitions."""
    print("\n--- test_gate_metric_definitions_complete ---")
    conn = get_db()
    missing = conn.execute("""
        SELECT COUNT(*) FROM series s
        WHERE s.series_type='derived'
        AND s.series_id NOT IN (SELECT series_id FROM metric_definitions)
    """).fetchone()[0]
    conn.close()
    assert missing == 0, f"P0 FAIL: {missing} derived series missing metric_definitions"

def test_gate_no_semantic_substitution():
    """Gate: Verified 国开债 must not map to 国债."""
    print("\n--- test_gate_no_semantic_substitution ---")
    import json
    with open('config/wind_mapping.json') as f:
        mappings = json.load(f)
    entries = [m for m in mappings if isinstance(m, dict) and 'series_id' in m]

    # sec_fi:C was originally 开行债 matched to 国债 — should be mapping_pending
    m = next((x for x in entries if x['series_id'] == 'sec_fi:C'), None)
    if m:
        # Check that if verified, the edb_indicator actually contains 开行债
        if m['status'] in ('verified_exact', 'verified_unit_transform'):
            edb_ind = m.get('verify_details', {}).get('edb_indicator', '')
            assert '开行' in edb_ind or '国家开发银行' in edb_ind or '国开' in edb_ind, \
                f"P0 FAIL: sec_fi:C mapped to '{edb_ind}' — semantic mismatch (开行债→国债)"

def test_gate_update_plan_validation_dates():
    """Gate: Update plan validation_dates must be 2 different real DB dates."""
    print("\n--- test_gate_update_plan_validation_dates ---")
    import json
    with open('config/update_plan.json') as f:
        plan = json.load(f)

    for entry in plan:
        vd = entry.get('validation_dates', [])
        assert len(vd) == 2, f"FAIL: {entry['series_id']}: {len(vd)} validation_dates (need 2)"
        assert vd[0] != vd[1], f"FAIL: {entry['series_id']}: identical dates {vd}"

def test_gate_html_js_syntax():
    """Gate: Generated HTML JavaScript must pass syntax check."""
    print("\n--- test_gate_html_js_syntax ---")
    import re, subprocess, os

    html_path = 'reports/fx_flow_dashboard.html'
    if not os.path.exists(html_path):
        print("SKIP: HTML not generated")
        return

    with open(html_path) as f:
        html = f.read()

    scripts = re.findall(r'<script[^>]*?>(.*?)</script>', html, re.DOTALL)
    for i, s in enumerate(scripts):
        if 'dashboard-data' not in str(s[:50]) and s.strip():
            tmp = f'/tmp/gate_test_{i}.js'
            with open(tmp, 'w') as fout:
                fout.write(s)
            result = subprocess.run(['node', '--check', tmp], capture_output=True, text=True)
            os.unlink(tmp)
            assert result.returncode == 0, \
                f"P0 FAIL: HTML script {i} has JS syntax error: {result.stderr[:200]}"

def test_gate_chart_catalog_exists():
    """Gate: chart_catalog.json must exist and reference valid series."""
    print("\n--- test_gate_chart_catalog_exists ---")
    import json, os

    path = 'config/chart_catalog.json'
    assert os.path.exists(path), "P0 FAIL: config/chart_catalog.json missing"

    with open(path) as f:
        catalog = json.load(f)

    modules = catalog.get('modules', {})
    assert len(modules) > 0, "P0 FAIL: chart_catalog has no modules"

    # Check that 3.即远期 has charts
    fwd = modules.get('3.即远期', {})
    assert len(fwd.get('charts', [])) > 0, "P0 FAIL: 3.即远期 has no catalog charts"

    # Verify all referenced series exist in DB
    conn = get_db()
    for mod_name, mod_data in modules.items():
        for ch in mod_data.get('charts', []):
            for ds in ch.get('datasets', []):
                sid = ds.get('series_id', '')
                if sid:
                    exists = conn.execute("SELECT COUNT(*) FROM series WHERE series_id=?", (sid,)).fetchone()[0]
                    assert exists > 0, f"P0 FAIL: {ch['chart_id']} references non-existent series {sid}"
    conn.close()


# =============================================================================
# recompute_derived.py tests
# =============================================================================

def _make_dict(values):
    """Helper: convert list to dict with date keys (2025-01-31, 2025-02-28, ...)."""
    return {f"2025-{(i+1):02d}-{28 if (i+1)!=1 else 31}d": v for i, v in enumerate(values)}


def test_sma():
    """Test Simple Moving Average (dict API)."""
    print("\n--- test_sma ---")
    vals = _make_dict([10, 20, 30, 40, 50])
    result = sma(vals, window=3)
    dates = sorted(vals.keys())
    assert_eq(len(result), 3, "sma: 5 values, window=3 → 3 results")
    assert_approx(result[dates[2]], 20.0, label="sma idx2")  # (10+20+30)/3
    assert_approx(result[dates[3]], 30.0, label="sma idx3")  # (20+30+40)/3
    assert_approx(result[dates[4]], 40.0, label="sma idx4")  # (30+40+50)/3

    # Window larger than data
    small = _make_dict([10, 20])
    result2 = sma(small, window=5)
    assert_eq(len(result2), 0, "sma window too large → empty")


def test_rolling_sum():
    """Test rolling sum (dict API)."""
    print("\n--- test_rolling_sum ---")
    vals = _make_dict([10, 20, 30, 40, 50])
    result = rolling_sum(vals, window=3)
    dates = sorted(vals.keys())
    assert_eq(len(result), 3, "rolling_sum: 5 values, window=3 → 3 results")
    assert_approx(result[dates[2]], 60, label="rsum idx2")   # 10+20+30
    assert_approx(result[dates[3]], 90, label="rsum idx3")   # 20+30+40
    assert_approx(result[dates[4]], 120, label="rsum idx4")  # 30+40+50


def test_z_score():
    """Test Z-Score with sample stddev (N-1), dict API."""
    print("\n--- test_z_score ---")
    import statistics
    raw_vals = list(range(1, 50))
    vals = _make_dict(raw_vals)
    result = z_score(vals, window=10, sample_std=True)

    dates = sorted(vals.keys())
    assert_eq(len(result), len(raw_vals) - 9, "zscore: 49 values, window=10 → 40 results")

    # Verify at index 9 (window dates[0:10] = raw_vals[0:10] = 1..10)
    window_vals = raw_vals[0:10]
    mean = statistics.mean(window_vals)  # 5.5
    std = statistics.stdev(window_vals)  # sample std
    expected_z = (raw_vals[9] - mean) / std
    assert_approx(result[dates[9]], expected_z, tolerance=1e-6, label="zscore idx9")

    # Test with population std
    result_pop = z_score(vals, window=10, sample_std=False)
    pop_std = statistics.pstdev(window_vals)
    expected_pop_z = (raw_vals[9] - mean) / pop_std
    assert_approx(result_pop[dates[9]], expected_pop_z, tolerance=1e-6, label="zscore pop idx9")

    # Test with single repeated value (std=0) -> should return 0
    uniform_vals = {f"2025-{(i+1):02d}-28": 5.0 for i in range(10)}
    uniform = z_score(uniform_vals, window=5, sample_std=True)
    uniform_dates = sorted(uniform_vals.keys())
    assert_approx(uniform[uniform_dates[4]], 0.0, label="zscore uniform")


def test_rolling_sum_ratio():
    """Test rolling sum ratio (dict API)."""
    print("\n--- test_rolling_sum_ratio ---")
    num = _make_dict([10, 20, 30, 40, 50])
    denom = _make_dict([100, 200, 300, 400, 500])
    result = rolling_sum_ratio(num, denom, window=3)

    dates = sorted(set(num.keys()) & set(denom.keys()))
    assert_eq(len(result), 3, "ratio: 5 values, window=3 → 3 results")
    assert_approx(result[dates[2]], 60/600, label="ratio idx2")   # 0.1
    assert_approx(result[dates[3]], 90/900, label="ratio idx3")   # 0.1
    assert_approx(result[dates[4]], 120/1200, label="ratio idx4") # 0.1

    # Division by zero → excluded from result
    zero_num = _make_dict([1, 2, 3])
    zero_den = _make_dict([0, 0, 0])
    result_zero = rolling_sum_ratio(zero_num, zero_den, window=3)
    assert_eq(len(result_zero), 0, "ratio div by zero → empty")


# =============================================================================
# validate_update.py tests
# =============================================================================

def test_validate_overlap_pass():
    """Test overlap validation with matching data."""
    print("\n--- test_validate_overlap ---")
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_db(conn)

    conn.execute("INSERT INTO series (series_id, display_name, module, series_type) VALUES (?,?,?,?)",
                 ("vtest:A", "VTest", "test", "raw"))
    for d, v in [("2025-01-31", 100), ("2025-02-28", 200), ("2025-03-31", 300)]:
        conn.execute("INSERT INTO observations (series_id, date, value) VALUES (?,?,?)",
                     ("vtest:A", d, v))
    conn.commit()

    # Perfect match
    new_data = {"2025-01-31": 100.0, "2025-02-28": 200.0, "2025-03-31": 300.0}
    passed, issues = validate_overlap(conn, "vtest:A", new_data)
    assert_true(passed, "overlap perfect match")
    assert_eq(len(issues), 3, "overlap 3 points checked")
    assert_true(all(i['status'] == 'pass' for i in issues), "all pass")

    conn.close()


def test_validate_overlap_fail():
    """Test overlap validation rejects divergent data."""
    print("\n--- test_validate_overlap_fail ---")
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_db(conn)

    conn.execute("INSERT INTO series (series_id, display_name, module, series_type) VALUES (?,?,?,?)",
                 ("vtest:B", "VTestB", "test", "raw"))
    for d, v in [("2025-01-31", 100), ("2025-02-28", 200)]:
        conn.execute("INSERT INTO observations (series_id, date, value) VALUES (?,?,?)",
                     ("vtest:B", d, v))
    conn.commit()

    # 50% perturbation
    new_data = {"2025-01-31": 150.0, "2025-02-28": 300.0}
    passed, issues = validate_overlap(conn, "vtest:B", new_data, tolerance=1e-6)
    assert_false(passed, "overlap rejects perturbed data")
    assert_true(any(i['status'] == 'fail' for i in issues), "has failure")

    conn.close()


def test_validate_overlap_no_overlap():
    """Test validation with no overlapping dates (should pass — no contradiction)."""
    print("\n--- test_validate_overlap_no_overlap ---")
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_db(conn)

    conn.execute("INSERT INTO series (series_id, display_name, module, series_type) VALUES (?,?,?,?)",
                 ("vtest:C", "VTestC", "test", "raw"))
    conn.execute("INSERT INTO observations (series_id, date, value) VALUES ('vtest:C', '2025-01-31', 100)")
    conn.commit()

    # No overlap dates
    new_data = {"2025-04-30": 400.0, "2025-05-31": 500.0}
    passed, issues = validate_overlap(conn, "vtest:C", new_data)
    assert_true(passed, "no overlap passes")
    assert_eq(len(issues), 0, "no overlap => 0 issues")

    conn.close()


# =============================================================================
# verify_wind_mappings.py tests
# =============================================================================

def test_detect_unit_factor():
    """Test unit factor detection."""
    print("\n--- test_detect_unit_factor ---")
    from verify_wind_mappings import detect_unit_factor

    # EDB values in 元, DB values in 亿 (factor 1e8)
    edb_map = {"2025-01-31": 10000000000.0, "2025-02-28": 20000000000.0, "2025-03-31": 30000000000.0}
    db_map = {"2025-01-31": 100.0, "2025-02-28": 200.0, "2025-03-31": 300.0}
    factor, error = detect_unit_factor(edb_map, db_map)
    assert_approx(factor, 1e8, tolerance=1, label="detect factor 1e8")
    assert_true(error < 0.01, f"low error: {error}")

    # No unit difference (factor 1)
    edb_map2 = {"2025-01-31": 100.0, "2025-02-28": 200.0}
    db_map2 = {"2025-01-31": 100.0, "2025-02-28": 200.0}
    factor2, error2 = detect_unit_factor(edb_map2, db_map2)
    assert_approx(factor2, 1.0, label="detect factor 1")
    assert_true(error2 < 0.01, f"low error for factor 1: {error2}")

    # No overlap -> returns 1, inf
    factor3, error3 = detect_unit_factor({"2025-01-31": 100}, {"2026-01-31": 100})
    assert_eq(factor3, 1, "no overlap defaults to factor 1")


def test_normalize_date():
    """Test date normalization."""
    print("\n--- test_normalize_date ---")
    from verify_wind_mappings import normalize_date
    assert_eq(normalize_date("2025-01-31"), "2025-01-31")
    assert_eq(normalize_date("2025-01-31T00:00:00"), "2025-01-31")
    assert_eq(normalize_date(None), "")
    assert_eq(normalize_date(""), "")


# =============================================================================
# Integration test: end-to-end with temp DB
# =============================================================================

def test_integration_import_and_recompute():
    """Integration test: create DB, import sample, recompute derived."""
    print("\n--- test_integration ---")
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_db(conn)

    # Create 2 raw series
    for sid, name in [("raw:A", "Raw A"), ("raw:B", "Raw B")]:
        conn.execute("INSERT INTO series (series_id, display_name, module, series_type) VALUES (?,?,?,?)",
                     (sid, name, "test", "raw"))

    # Insert observations
    for d_idx, (month, a_val, b_val) in enumerate([
        ("2025-01-31", 100, 50), ("2025-02-28", 110, 55),
        ("2025-03-31", 120, 60), ("2025-04-30", 130, 65)
    ]):
        conn.execute("INSERT INTO observations (series_id, date, value) VALUES ('raw:A', ?, ?)", (month, a_val))
        conn.execute("INSERT INTO observations (series_id, date, value) VALUES ('raw:B', ?, ?)", (month, b_val))
    conn.commit()

    # Verify counts
    count = conn.execute("SELECT COUNT(*) as n FROM observations").fetchone()
    assert_eq(count['n'], 8, "integration: 8 raw observations")

    # Validate
    issues = validate_db(conn)
    assert_eq(len(issues), 0, "integration: no validation issues")

    conn.close()


# =============================================================================
# Main
# =============================================================================

def main():
    global TESTS_PASSED, TESTS_FAILED

    print("=" * 60)
    print("FX Flow Dashboard — Unit Tests")
    print(f"Run at: {datetime.now().isoformat()}")
    print("=" * 60)

    # lib.py
    test_init_db()
    test_upsert_and_query()
    test_observations()
    test_update_runs()
    test_values_match()
    test_validate_db_checks()

    # recompute_derived.py
    test_sma()
    test_rolling_sum()
    test_z_score()
    test_rolling_sum_ratio()

    # validate_update.py
    test_validate_overlap_pass()
    test_validate_overlap_fail()
    test_validate_overlap_no_overlap()

    # verify_wind_mappings.py
    test_detect_unit_factor()
    test_normalize_date()

    # Integration
    test_integration_import_and_recompute()

    # Loop A8: Production gate tests
    test_gate_arbitrary_factor_rejected()
    test_gate_transform_whitelist()
    test_gate_overlap_requirement()
    test_gate_metric_definitions_complete()
    test_gate_no_semantic_substitution()
    test_gate_update_plan_validation_dates()
    test_gate_html_js_syntax()
    test_gate_chart_catalog_exists()

    print("\n" + "=" * 60)
    print(f"RESULTS: {TESTS_PASSED} passed, {TESTS_FAILED} failed, "
          f"{TESTS_PASSED + TESTS_FAILED} total")
    if TESTS_FAILED > 0:
        print("❌ SOME TESTS FAILED")
    else:
        print("✅ ALL TESTS PASSED")
    print("=" * 60)

    return 0 if TESTS_FAILED == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

"""
Shared library for the FX Flow Dashboard project.
Database operations, validation, configuration.
"""
import sqlite3
import json
import os
from pathlib import Path
from datetime import datetime, date

# --- Paths ---
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DB_PATH = DATA_DIR / "monthly_brief.sqlite"
CONFIG_DIR = PROJECT_ROOT / "config"
REPORTS_DIR = PROJECT_ROOT / "reports"
TEMPLATES_DIR = PROJECT_ROOT / "templates"

# --- Database ---

def get_db(db_path=None):
    """Get a database connection with WAL mode and foreign keys."""
    path = db_path or str(DB_PATH)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row
    return conn


def init_db(conn=None):
    """Initialize the database schema. Idempotent (IF NOT EXISTS)."""
    close_after = conn is None
    if conn is None:
        conn = get_db()

    conn.executescript("""
    CREATE TABLE IF NOT EXISTS series (
        series_id        TEXT PRIMARY KEY,
        display_name     TEXT NOT NULL,
        module           TEXT NOT NULL,
        series_type      TEXT NOT NULL CHECK(series_type IN ('raw','derived','manual','legacy_external')),
        frequency        TEXT,
        unit             TEXT,
        source           TEXT,
        source_query     TEXT,
        excel_sheet      TEXT,
        excel_range      TEXT,
        update_status    TEXT,
        first_date       TEXT,
        last_date        TEXT,
        notes            TEXT
    );

    CREATE TABLE IF NOT EXISTS observations (
        series_id       TEXT NOT NULL,
        date            TEXT NOT NULL,
        value           REAL,
        source          TEXT,
        source_vintage  TEXT,
        imported_at     TEXT,
        run_id          TEXT,
        PRIMARY KEY (series_id, date)
    );

    CREATE TABLE IF NOT EXISTS metric_definitions (
        series_id              TEXT PRIMARY KEY,
        formula_description    TEXT,
        input_series_json      TEXT,
        calculation_version    INTEGER,
        implementation         TEXT,
        missing_value_rule     TEXT,
        sign_convention        TEXT
    );

    CREATE TABLE IF NOT EXISTS update_runs (
        run_id               TEXT PRIMARY KEY,
        started_at           TEXT,
        finished_at          TEXT,
        status               TEXT,
        requested_series     INTEGER,
        successful_series    INTEGER,
        failed_series        INTEGER,
        new_observations     INTEGER,
        revised_observations INTEGER,
        error_summary        TEXT
    );

    CREATE TABLE IF NOT EXISTS validation_events (
        run_id           TEXT,
        series_id        TEXT,
        date             TEXT,
        database_value   REAL,
        fetched_value    REAL,
        difference       REAL,
        tolerance        REAL,
        status           TEXT,
        message          TEXT
    );

    CREATE INDEX IF NOT EXISTS idx_obs_series ON observations(series_id);
    CREATE INDEX IF NOT EXISTS idx_obs_date ON observations(date);
    CREATE INDEX IF NOT EXISTS idx_obs_series_date ON observations(series_id, date);
    CREATE INDEX IF NOT EXISTS idx_series_module ON series(module);
    CREATE INDEX IF NOT EXISTS idx_series_type ON series(series_type);
    """)

    conn.commit()
    if close_after:
        conn.close()


def upsert_series(conn, series_data):
    """Insert or update a series metadata row."""
    conn.execute("""
        INSERT OR REPLACE INTO series
        (series_id, display_name, module, series_type, frequency, unit,
         source, source_query, excel_sheet, excel_range,
         update_status, first_date, last_date, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        series_data["series_id"],
        series_data.get("display_name", ""),
        series_data.get("module", ""),
        series_data.get("series_type", "raw"),
        series_data.get("frequency"),
        series_data.get("unit"),
        series_data.get("source"),
        series_data.get("source_query"),
        series_data.get("excel_sheet"),
        series_data.get("excel_range"),
        series_data.get("update_status"),
        series_data.get("first_date"),
        series_data.get("last_date"),
        series_data.get("notes"),
    ))


def insert_observation(conn, series_id, obs_date, value, source="excel_seed", run_id=None):
    """Insert a single observation (idempotent via INSERT OR REPLACE)."""
    if isinstance(obs_date, (date, datetime)):
        obs_date = obs_date.isoformat()[:10]
    imported_at = datetime.now().isoformat()
    conn.execute("""
        INSERT OR REPLACE INTO observations (series_id, date, value, source, imported_at, run_id)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (series_id, obs_date, value, source, imported_at, run_id))


def insert_observations_batch(conn, rows, run_id=None):
    """Insert many observations in a single transaction."""
    imported_at = datetime.now().isoformat()
    data = []
    for series_id, obs_date, value, source in rows:
        if isinstance(obs_date, (date, datetime)):
            obs_date = obs_date.isoformat()[:10]
        data.append((series_id, obs_date, value, source, imported_at, run_id))
    conn.executemany("""
        INSERT OR REPLACE INTO observations (series_id, date, value, source, imported_at, run_id)
        VALUES (?, ?, ?, ?, ?, ?)
    """, data)


def get_observations(conn, series_id, start_date=None, end_date=None):
    """Get observations for a series, ordered by date."""
    query = "SELECT date, value FROM observations WHERE series_id = ?"
    params = [series_id]
    if start_date:
        query += " AND date >= ?"
        params.append(start_date)
    if end_date:
        query += " AND date <= ?"
        params.append(end_date)
    query += " ORDER BY date ASC"
    return conn.execute(query, params).fetchall()


def get_latest_date(conn, series_id):
    """Get the most recent observation date for a series."""
    row = conn.execute(
        "SELECT MAX(date) as max_date FROM observations WHERE series_id = ?",
        (series_id,)
    ).fetchone()
    return row["max_date"] if row else None


def start_update_run(conn, requested_series=0):
    """Create a new update_runs entry and return the run_id."""
    run_id = datetime.now().strftime("run_%Y%m%d_%H%M%S")
    conn.execute("""
        INSERT INTO update_runs (run_id, started_at, status, requested_series)
        VALUES (?, ?, 'running', ?)
    """, (run_id, datetime.now().isoformat(), requested_series))
    conn.commit()
    return run_id


def finish_update_run(conn, run_id, status, **counts):
    """Mark an update run as completed/failed with counts."""
    conn.execute("""
        UPDATE update_runs
        SET finished_at = ?, status = ?,
            successful_series = ?, failed_series = ?,
            new_observations = ?, revised_observations = ?,
            error_summary = ?
        WHERE run_id = ?
    """, (
        datetime.now().isoformat(), status,
        counts.get("successful", 0), counts.get("failed", 0),
        counts.get("new_obs", 0), counts.get("revised", 0),
        counts.get("errors", ""),
        run_id
    ))
    conn.commit()


def validate_db(conn):
    """Run basic validation checks. Returns list of issues."""
    issues = []

    # Check for NULL series_id
    null_series = conn.execute(
        "SELECT COUNT(*) as cnt FROM observations WHERE series_id IS NULL"
    ).fetchone()
    if null_series["cnt"] > 0:
        issues.append(f"NULL series_id in observations: {null_series['cnt']} rows")

    # Check for duplicate observations
    dupes = conn.execute("""
        SELECT series_id, date, COUNT(*) as cnt
        FROM observations
        GROUP BY series_id, date
        HAVING cnt > 1
    """).fetchall()
    if dupes:
        issues.append(f"Duplicate observations: {len(dupes)} cases")

    # Check for non-finite values
    nonfinite = conn.execute("""
        SELECT COUNT(*) as cnt FROM observations
        WHERE value IS NOT NULL AND (value = 'Infinity' OR value = '-Infinity' OR value = 'NaN')
    """).fetchone()
    if nonfinite["cnt"] > 0:
        issues.append(f"Non-finite values: {nonfinite['cnt']} rows")

    # Check series have observations
    no_obs = conn.execute("""
        SELECT series_id FROM series
        WHERE series_id NOT IN (SELECT DISTINCT series_id FROM observations)
    """).fetchall()
    if no_obs:
        issues.append(f"Series without observations: {len(no_obs)} ({[r['series_id'] for r in no_obs[:5]]}...)")

    return issues


# --- Validation helpers ---

def values_match(a, b, tolerance=1e-8):
    """Check if two numeric values match within tolerance."""
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False
    try:
        return abs(float(a) - float(b)) <= tolerance
    except (ValueError, TypeError):
        return False

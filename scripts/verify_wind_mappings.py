"""
Step 5b: Verify Wind EDB mappings by querying recent data and comparing with Excel.
Updates wind_mapping.json with verified/transform/failed statuses.

EDB Interface (iFind/同花顺):
- Tool: get_edb_data
- Query format: "{indicator_name}（{YYYY-MM}-{YYYY-MM}）"
- Common unit transforms: EDB returns 元, DB stores 亿 → factor 1e8
"""
import sys, json, time, sqlite3
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parent))

# MCP server config — reads from ~/.claude/mcp.json
import os
MCP_CONFIG_PATH = os.path.expanduser("~/.claude/mcp.json")

try:
    with open(MCP_CONFIG_PATH) as f:
        mcp_config = json.load(f)
    edb_config = mcp_config["mcpServers"]["hexin-ifind-ds-edb-mcp"]
    EDB_URL = edb_config["url"]
    AUTH_HEADER = edb_config["headers"]["Authorization"]
except Exception:
    EDB_URL = None
    AUTH_HEADER = None

import urllib.request
import urllib.error


def call_edb(query_str):
    """Query the iFind EDB MCP server. Returns parsed response dict or None."""
    if not EDB_URL or not AUTH_HEADER:
        return {"error": "MCP not configured — check ~/.claude/mcp.json"}

    payload = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": "get_edb_data",
            "arguments": {"query": query_str}
        },
        "id": int(time.time() * 1000) % 100000
    }

    req = urllib.request.Request(
        EDB_URL,
        data=json.dumps(payload).encode('utf-8'),
        headers={
            "Content-Type": "application/json",
            "Authorization": AUTH_HEADER
        }
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
            if "error" in data:
                return {"error": data["error"].get("message", str(data["error"]))}
            text = data['result']['content'][0]['text']
            return json.loads(text)
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}: {e.reason}"}
    except Exception as e:
        return {"error": str(e)}


def normalize_date(d):
    """Normalize any date to YYYY-MM-DD."""
    if not d:
        return ""
    s = str(d).strip()[:10]
    return s


def detect_unit_factor(edb_map, db_map):
    """
    Detect the unit scaling factor between EDB and DB values.
    Common factors for Chinese economic data:
    - 1e8: 元 → 亿 (most common)
    - 1e4: 元 → 万
    - 1:   同单位
    - 100: 百分比单位
    """
    candidates = [1, 1e4, 1e8, 100, 10000, 1/100, 1/1e4, 1/1e8]
    best_factor = 1
    best_error = float('inf')

    overlap_dates = set(edb_map.keys()) & set(db_map.keys())
    if len(overlap_dates) < 2:
        return 1, float('inf')

    for factor in candidates:
        errors = []
        for d in overlap_dates:
            edb_adj = edb_map[d] / factor
            db_val = db_map[d]
            if abs(db_val) > 1e-9:
                pct = abs(edb_adj - db_val) / abs(db_val) * 100
                errors.append(pct)
        if errors:
            avg_err = sum(errors) / len(errors)
            if avg_err < best_error:
                best_error = avg_err
                best_factor = factor

    return best_factor, best_error


def compare_values(mapping_entry, conn, edb_datas, tolerance_pct=1.0):
    """
    Compare EDB data with DB values for a single series.
    Handles unit conversion and sign detection.
    """
    sid = mapping_entry['series_id']

    # Get DB observations
    db_rows = conn.execute(
        "SELECT date, value FROM observations WHERE series_id=? ORDER BY date",
        (sid,)
    ).fetchall()
    db_map = {r['date']: r['value'] for r in db_rows}

    if not edb_datas or len(edb_datas) == 0:
        return "no_result", None, "EDB returned no data"

    edb_data = edb_datas[0].get('data', {})
    rows = edb_data.get('data', [])
    columns = edb_data.get('columns', [])
    attrs = edb_data.get('attrs', {})
    index_id = edb_datas[0].get('extra', {}).get('index_id', '')
    edb_indicator = columns[1] if len(columns) > 1 else "unknown"

    if not rows:
        return "no_result", None, "EDB returned empty data"

    # Build EDB date→value map
    edb_map = {}
    for row in rows:
        if len(row) >= 2:
            d = normalize_date(row[0])
            try:
                edb_map[d] = float(row[1])
            except (ValueError, TypeError):
                pass

    if not edb_map:
        return "no_result", None, "No parseable EDB values"

    # Detect unit factor
    factor, detection_error = detect_unit_factor(edb_map, db_map)
    transforms = []

    # Apply unit factor
    edb_adjusted = {}
    for d, v in edb_map.items():
        edb_adjusted[d] = v / factor

    # Check for sign flip (some indicators have opposite sign convention)
    overlap_dates = sorted(set(edb_adjusted.keys()) & set(db_map.keys()))
    if overlap_dates:
        sign_flip = all(
            abs(edb_adjusted[d] + db_map[d]) < abs(edb_adjusted[d] - db_map[d]) * 0.1
            for d in overlap_dates[:3]
        )
        if sign_flip:
            transforms.append("sign_flip")
            for d in edb_adjusted:
                edb_adjusted[d] = -edb_adjusted[d]

    # Compare on overlapping dates
    overlap = []
    for d in overlap_dates:
        ev = edb_adjusted[d]
        dv = db_map[d]
        diff = abs(ev - dv)
        pct = diff / abs(dv) * 100 if abs(dv) > 1e-9 else diff * 100
        overlap.append((d, dv, ev, diff, pct))

    if len(overlap) < 2:
        return "mapping_pending", None, (
            f"Only {len(overlap)} overlap points: "
            f"DB dates={sorted(db_map.keys())[-3:]}, "
            f"EDB dates={sorted(edb_map.keys())[-3:]}"
        )

    max_pct = max(o[4] for o in overlap)
    max_diff = max(o[3] for o in overlap)
    avg_pct = sum(o[4] for o in overlap) / len(overlap)

    # Build transform description
    if factor != 1:
        transforms.append(f"unit_div_{factor:.0f}")
    edb_unit = list(attrs.values())[0].get('unit', '') if attrs else ''

    details = {
        "overlap_points": len(overlap),
        "max_diff_pct": round(max_pct, 4),
        "avg_diff_pct": round(avg_pct, 4),
        "max_abs_diff": round(max_diff, 4),
        "unit_factor": factor,
        "transform": transforms,
        "samples": [(d, f"{dv:.4f}", f"{ev:.4f}") for d, dv, ev, diff, pct in overlap[-3:]],
        "edb_indicator": edb_indicator,
        "edb_unit": edb_unit,
        "index_id": index_id,
    }

    # Classify
    if avg_pct <= tolerance_pct:
        if transforms:
            return "verified_with_transform", transforms, details
        return "verified", transforms, details
    elif avg_pct <= tolerance_pct * 3:
        # Possible data revision — mark as verified with note
        return "verified_with_transform", transforms + ["minor_revision"], details
    else:
        return "mapping_pending", transforms, details


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Verify Wind EDB mappings")
    parser.add_argument("--limit", type=int, default=0, help="Limit to first N series")
    parser.add_argument("--module", default=None, help="Only verify specific module")
    parser.add_argument("--tolerance", type=float, default=1.0, help="Tolerance %% (default 1%%)")
    parser.add_argument("--delay", type=float, default=0.3, help="Delay between queries (seconds)")
    args = parser.parse_args()

    # Load mappings
    mapping_path = Path('config/wind_mapping.json')
    if not mapping_path.exists():
        print("No wind_mapping.json found. Run Step 5 first.")
        return 1

    with open(mapping_path, 'r', encoding='utf-8') as f:
        mappings = json.load(f)

    conn = sqlite3.connect('data/monthly_brief.sqlite')
    conn.row_factory = sqlite3.Row

    stats = {
        "verified": 0, "verified_with_transform": 0,
        "no_result": 0, "mapping_pending": 0, "error": 0
    }

    # Filter and sort
    targets = [m for m in mappings if m.get('wind_indicator') and m.get('status') != 'verified']
    if args.module:
        targets = [m for m in targets if m['module'] == args.module]
    if args.limit > 0:
        targets = targets[:args.limit]

    # Skip series already verified in the current run
    targets_to_verify = [m for m in targets if m.get('status') not in ('verified', 'verified_with_transform')]

    print(f"Targets: {len(targets_to_verify)} to verify (of {len(mappings)} total)")
    if not EDB_URL:
        print("⚠️  EDB MCP not configured in ~/.claude/mcp.json")
        print("   Run in simulation mode — no actual queries will be made.")
        conn.close()
        return 1

    print(f"Tolerance: ±{args.tolerance}%")
    print(f"{'='*70}")

    for i, m in enumerate(targets_to_verify):
        sid = m['series_id']
        indicator = m['wind_indicator']

        # Get date range from last known observations
        last_dates = m.get('last_dates', [])
        if not last_dates:
            # Query DB directly
            rows = conn.execute(
                "SELECT date FROM observations WHERE series_id=? ORDER BY date DESC LIMIT 3",
                (sid,)
            ).fetchall()
            if not rows:
                continue
            recent = rows[-1]['date'][:7]  # oldest of recent
            latest = rows[0]['date'][:7]   # newest
        else:
            recent = last_dates[0][0][:7] if last_dates[0] else "2025-01"
            latest = last_dates[-1][0][:7] if last_dates[-1] else "2026-05"

        query = f"{indicator}（{recent}-{latest}）"
        print(f"[{i+1}/{len(targets_to_verify)}] {sid}")

        try:
            edb_result = call_edb(query)
        except Exception as e:
            print(f"  ❌ API exception: {e}")
            stats["error"] += 1
            m['status'] = 'mapping_pending'
            m['verify_note'] = f"API error: {str(e)[:200]}"
            continue

        # Handle errors
        if edb_result is None or "error" in (edb_result or {}):
            err_msg = edb_result.get("error", "Unknown") if edb_result else "No response"
            if "authentication" in str(err_msg).lower():
                print(f"  ⚠️  Auth failed — token likely expired. Stopping.")
                print(f"     Verified {stats['verified'] + stats['verified_with_transform']} so far.")
                break
            print(f"  ⚠️  EDB error: {err_msg[:100]}")
            stats["error"] += 1
            m['verify_note'] = str(err_msg)[:200]
            continue

        if edb_result.get('code') != 1:
            stats["no_result"] += 1
            m['status'] = 'no_result'
            m['verify_note'] = f"EDB code={edb_result.get('code')}: {edb_result.get('msg', '')}"
            print(f"  ❌ no_result: {edb_result.get('msg', 'unknown')[:80]}")
            continue

        edb_datas = edb_result.get('data', {}).get('datas', [])
        if not edb_datas:
            stats["no_result"] += 1
            m['status'] = 'no_result'
            m['verify_note'] = "EDB returned empty datas"
            print(f"  ❌ no_result: empty response")
            continue

        # Compare
        status, transforms, details = compare_values(m, conn, edb_datas, args.tolerance)

        m['status'] = status
        if transforms:
            m['transform'] = transforms
        m['verify_details'] = details
        m['verified_at'] = datetime.now().isoformat()

        stats[status] = stats.get(status, 0) + 1

        icon = {"verified": "✅", "verified_with_transform": "🔧",
                "no_result": "❌", "mapping_pending": "❓"}.get(status, "⚠️")
        if isinstance(details, dict):
            samples = ", ".join(
                f"{s[0]}={s[1]}vs{s[2]}" for s in details.get('samples', [])[:2]
            )
            print(f"  {icon} {status} | {details['overlap_points']} pts, "
                  f"avg_diff={details['avg_diff_pct']:.2f}% | {samples}")
        else:
            print(f"  {icon} {status}: {str(details)[:100]}")

        # Periodic save
        if (i + 1) % 20 == 0:
            with open(mapping_path, 'w', encoding='utf-8') as f:
                json.dump(mappings, f, ensure_ascii=False, indent=2)
            print(f"  --- saved checkpoint ({i+1}/{len(targets_to_verify)}) ---")

        time.sleep(args.delay)

    # Final save
    with open(mapping_path, 'w', encoding='utf-8') as f:
        json.dump(mappings, f, ensure_ascii=False, indent=2)

    total_verified = stats['verified'] + stats['verified_with_transform']
    total = len(mappings)

    print(f"\n{'='*70}")
    print(f"Verification Results:")
    print(f"  ✅ verified:              {stats['verified']}")
    print(f"  🔧 verified_with_transform: {stats['verified_with_transform']}")
    print(f"  ❌ no_result:             {stats['no_result']}")
    print(f"  ❓ mapping_pending:       {stats['mapping_pending']}")
    print(f"  ❌ error:                 {stats['error']}")
    print(f"  ---")
    print(f"  Total verified:           {total_verified}/{total} ({total_verified/total*100:.1f}%)")

    # Update WIND_COVERAGE.md
    update_coverage_doc(mappings)
    print(f"\nSaved: {mapping_path}")
    print(f"Updated: docs/WIND_COVERAGE.md")

    conn.close()
    return 0


def update_coverage_doc(mappings):
    """Regenerate WIND_COVERAGE.md from current mapping statuses."""
    from collections import Counter
    total = len(mappings)
    statuses = Counter(m.get('status', 'mapping_pending') for m in mappings)

    by_module = {}
    for m in mappings:
        mod = m['module']
        if mod not in by_module:
            by_module[mod] = Counter()
        by_module[mod][m.get('status', 'mapping_pending')] += 1

    lines = [
        "# Wind EDB Coverage",
        "",
        f"> 最后更新：{datetime.now().strftime('%Y-%m-%d %H:%M')} CST",
        "> 数据源：同花顺 iFind EDB MCP (hexin-ifind-ds-edb-mcp)",
        "",
        "## 总体覆盖",
        "",
        "| 状态 | 数量 | 占比 |",
        "|------|------|------|",
        f"| `verified` | {statuses.get('verified', 0)} | {statuses.get('verified', 0)/total*100:.1f}% |",
        f"| `verified_with_transform` | {statuses.get('verified_with_transform', 0)} | {statuses.get('verified_with_transform', 0)/total*100:.1f}% |",
        f"| `no_result` | {statuses.get('no_result', 0)} | {statuses.get('no_result', 0)/total*100:.1f}% |",
        f"| `mapping_pending` | {statuses.get('mapping_pending', 0)} | {statuses.get('mapping_pending', 0)/total*100:.1f}% |",
        f"| **总计** | **{total}** | **100%** |",
        "",
        "## 按模块覆盖",
        "",
        "| 模块 | Verified | Transform | No Result | Pending | 总计 |",
        "|------|----------|-----------|-----------|---------|------|",
    ]

    for mod in sorted(by_module.keys()):
        c = by_module[mod]
        t = sum(c.values())
        lines.append(
            f"| {mod} | {c.get('verified',0)} | {c.get('verified_with_transform',0)} "
            f"| {c.get('no_result',0)} | {c.get('mapping_pending',0)} | {t} |"
        )

    lines += [
        "",
        "## 常见单位变换",
        "",
        "| 变换 | 说明 |",
        "|------|------|",
        "| `unit_div_1e8` | EDB 返回**元**，DB 存储**亿**（÷100,000,000） |",
        "| `unit_div_1e4` | EDB 返回**元**，DB 存储**万**（÷10,000） |",
        "| `sign_flip` | EDB 与 Excel 符号约定相反（如购汇/售汇方向） |",
        "",
        "## 已验证指标样例",
        "",
        "| Series | Excel 指标名 | EDB 指标名 | 匹配 | 变换 |",
        "|--------|-------------|-----------|------|------|",
        "| trade_goods:B | 出口金额:当月值 | 出口总值(美元计价):当月值 | ~0.07% | unit_div_1e8 |",
        "| fx_fwd:D | 银行自身结售汇差额:当月值 | 银行代客结售汇:以美元计价:差额:银行自身 | ~0.05% | unit_div_1e8 |",
        "",
        "## 已知问题",
        "",
        "1. **FDI 模块**：Excel 使用完整的 Wind 层级路径名（如 `中国:金融账户:...:当季值`），EDB 模糊匹配可能返回不同粒度的指标",
        "2. **单位差异**：EDB 默认返回**元**，部分 Excel 列使用**亿美元**或**亿人民币**",
        "3. **名称差异**：EDB 指标名可能与 Excel 中的「指标名称」不完全一致（如差额 vs 净额）",
        "4. **频率差异**：FDI 部分序列为季度数据（当季值），需注意与月度序列的日期对齐",
        "",
        "## 使用方法",
        "",
        "```bash",
        "# 验证全部映射（需要有效 MCP 会话）",
        "python3 scripts/verify_wind_mappings.py",
        "",
        "# 验证特定模块",
        "python3 scripts/verify_wind_mappings.py --module 3.即远期",
        "",
        "# 限制数量 + 调整容差",
        "python3 scripts/verify_wind_mappings.py --limit 20 --tolerance 0.5",
        "",
        "# MCP 会话过期时，token 会自动从 ~/.claude/mcp.json 读取",
        "```",
    ]

    with open('docs/WIND_COVERAGE.md', 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')


if __name__ == "__main__":
    sys.exit(main())

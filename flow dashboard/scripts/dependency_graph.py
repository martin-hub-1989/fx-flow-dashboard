"""
dependency_graph.py — Derived metric dependency resolution.

Per NEXT_PHASE_EXECUTION_LOOP.md Loop 5: build the dependency graph from
metric_definitions.input_series_json so that a raw update recomputes only the
affected downstream derived series, in topological order, across >= 2 layers.
"""
import json


def build_dependents(conn):
    """Return {input_series_id: set(derived_series_id, ...)} reverse map."""
    dependents = {}
    rows = conn.execute(
        "SELECT series_id, input_series_json FROM metric_definitions"
    ).fetchall()
    for r in rows:
        sid = r["series_id"] if hasattr(r, "keys") else r[0]
        raw_json = r["input_series_json"] if hasattr(r, "keys") else r[1]
        if not raw_json:
            continue
        try:
            inputs = json.loads(raw_json)
        except (json.JSONDecodeError, TypeError):
            continue
        if isinstance(inputs, dict):
            inputs = list(inputs.values())
        for inp in inputs:
            if not isinstance(inp, str):
                continue
            dependents.setdefault(inp, set()).add(sid)
    return dependents


def affected_derived(conn, changed_series):
    """Return derived series affected by a change to `changed_series`,
    in topological order (a dependency appears before its dependents).

    Traverses transitively across multiple layers. Excludes the changed
    raw series themselves.
    """
    dependents = build_dependents(conn)

    # Collect all transitively-affected nodes via BFS.
    affected = set()
    frontier = list(changed_series)
    while frontier:
        node = frontier.pop()
        for dep in dependents.get(node, ()):
            if dep not in affected:
                affected.add(dep)
                frontier.append(dep)

    if not affected:
        return []

    # Topological sort restricted to affected nodes.
    # Build edges among affected: input -> derived.
    indeg = {n: 0 for n in affected}
    adj = {n: [] for n in affected}
    for inp, deps in dependents.items():
        for d in deps:
            if d in affected and inp in affected:
                adj[inp].append(d)
                indeg[d] += 1

    # Kahn's algorithm; deterministic by sorting.
    queue = sorted([n for n in affected if indeg[n] == 0])
    order = []
    while queue:
        n = queue.pop(0)
        order.append(n)
        for m in sorted(adj[n]):
            indeg[m] -= 1
            if indeg[m] == 0:
                queue.append(m)
                queue.sort()
    # Any cycle remainder appended deterministically.
    for n in sorted(affected):
        if n not in order:
            order.append(n)
    return order

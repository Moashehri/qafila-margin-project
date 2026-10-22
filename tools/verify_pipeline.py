"""Exercise two fresh datasets, re-runs, late corrections and Iceberg time travel.

    uv run python tools/verify_pipeline.py

Temporary inputs and warehouses are removed on exit. No existing data is changed.
The optional --report writes the measured results as JSON.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from run import PUBLISHED, get_catalog  # noqa: E402


def command(script: str, *args: str) -> None:
    subprocess.run([sys.executable, str(ROOT / script), *args], cwd=ROOT, check=True)


def capture(warehouse: Path) -> dict:
    catalog = get_catalog(warehouse)
    state = {}
    for name in PUBLISHED:
        table = catalog.load_table(name)
        rows = table.scan().to_arrow()
        rows = rows.sort_by([(column, "ascending") for column in rows.column_names])
        state[name] = {
            "uuid": str(table.metadata.table_uuid),
            "snapshots": [snapshot.snapshot_id for snapshot in table.snapshots()],
            "rows": rows,
        }
    return state


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def same_state(before: dict, after: dict) -> None:
    for name in PUBLISHED:
        for key in ("uuid", "snapshots"):
            require(before[name][key] == after[name][key], f"Re-run changed {name} {key}")
        require(before[name]["rows"].equals(after[name]["rows"]), f"Re-run changed {name} rows")


def margin_totals(rows) -> dict:
    return {column: round(sum(rows[column].to_pylist()), 2)
            for column in ("revenue_sar", "cost_sar", "margin_sar", "lines", "uncosted_lines")}


def verify(seed: int, folder: Path) -> dict:
    data, warehouse = folder / "data", folder / "warehouse"
    paths = ["--data-dir", str(data), "--warehouse", str(warehouse)]
    command("tools/make_data.py", "--seed", str(seed), "--out", str(data))
    command("run.py", *paths)
    command("tools/check.py", *paths)
    command("tools/reference_check.py", *paths)
    before = capture(warehouse)
    command("run.py", *paths)
    same_state(before, capture(warehouse))

    command("tools/make_data.py", "--out", str(data), "--add-correction")
    command("run.py", *paths)
    command("tools/check.py", *paths)
    command("tools/reference_check.py", *paths)
    after = capture(warehouse)
    catalog = get_catalog(warehouse)
    for name in PUBLISHED:
        require(before[name]["uuid"] == after[name]["uuid"], f"Correction recreated {name}")
        changed = not before[name]["rows"].equals(after[name]["rows"])
        expected_count = len(before[name]["snapshots"]) + int(changed)
        require(len(after[name]["snapshots"]) == expected_count, f"Unexpected snapshots: {name}")
        old = catalog.load_table(name).scan(snapshot_id=before[name]["snapshots"][-1]).to_arrow()
        old = old.sort_by([(column, "ascending") for column in old.column_names])
        require(old.equals(before[name]["rows"]), f"Old snapshot changed: {name}")
    command("run.py", *paths)
    same_state(after, capture(warehouse))
    results = json.loads((ROOT / "dbt/target/run_results.json").read_text())
    tests = [row for row in results["results"] if row["unique_id"].startswith("test.")]
    require(all(row["status"] == "pass" for row in tests), "dbt tests failed")
    return {
        "seed": seed,
        "dbt_tests_passed": len(tests),
        "independent_reference": "pass before and after correction",
        "idempotent": "pass before and after correction",
        "time_travel": "pass for all three tables",
        "tables": {name: {
            "rows_before": before[name]["rows"].num_rows,
            "rows_after": after[name]["rows"].num_rows,
            "snapshots_before": before[name]["snapshots"],
            "snapshots_after": after[name]["snapshots"],
        } for name in PUBLISHED},
        "margin_before": margin_totals(before["gold.weekly_margin"]["rows"]),
        "margin_after": margin_totals(after["gold.weekly_margin"]["rows"]),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", nargs="+", type=int, default=[2026, 11])
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    report = {"verified_at_utc": datetime.now(timezone.utc).isoformat(), "datasets": []}
    with TemporaryDirectory(prefix="qafila-verify-") as temporary:
        for index, seed in enumerate(args.seeds):
            report["datasets"].append(verify(seed, Path(temporary) / str(index)))
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

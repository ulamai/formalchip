#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from formalchip.config import load_config
from formalchip.kpi import compute_kpi_report


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate FormalChip gate/KPI policy for CI")
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--config", required=False)
    parser.add_argument("--baseline-csv", required=False)
    parser.add_argument("--out", required=False)
    args = parser.parse_args()

    policy = load_config(args.config).kpi if args.config else None
    baseline = Path(args.baseline_csv).resolve() if args.baseline_csv else None

    report = compute_kpi_report(Path(args.run_dir).resolve(), policy=policy, baseline_csv=baseline)
    payload = {
        "run_id": report.get("run_id"),
        "overall_success": report.get("overall_success"),
        "gate_verdict": report.get("gate_verdict"),
        "bug_or_coverage_achieved": report.get("bug_or_coverage_achieved"),
        "meets_time_reduction_target": report.get("meets_time_reduction_target"),
        "output": report.get("output"),
    }

    if args.out:
        out = Path(args.out).resolve()
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if bool(report.get("overall_success")) else 2


if __name__ == "__main__":
    raise SystemExit(main())

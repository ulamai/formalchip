from __future__ import annotations

import csv
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from .config import KPIConfig
from .reporting import build_gate_verdict, summarize_state_dict
from .util import utc_now_iso, write_json


def compute_kpi_report(
    run_dir: Path,
    policy: KPIConfig | None = None,
    baseline_csv: Path | None = None,
) -> dict[str, Any]:
    run_dir = run_dir.resolve()
    state_path = run_dir / "state.json"
    if not state_path.exists():
        raise FileNotFoundError(f"state.json not found under {run_dir}")

    state = json.loads(state_path.read_text(encoding="utf-8"))
    summary = summarize_state_dict(state)
    gate = build_gate_verdict(summary, kpi=policy)

    first_iter_metrics = _first_iteration_property_metrics(state)
    time_to_first_min = _time_to_first_meaningful_properties_min(state)

    baseline_eval = evaluate_baseline_study(baseline_csv) if baseline_csv else None
    effective_policy = policy or KPIConfig()

    time_reduction_meets = None
    if baseline_eval is not None and baseline_eval.get("avg_reduction_percent") is not None:
        time_reduction_meets = baseline_eval["avg_reduction_percent"] >= effective_policy.min_time_reduction_percent

    bug_or_coverage = bool(summary.get("bug_found")) or int(summary.get("coverage_hits", 0) or 0) > 0

    report = {
        "generated_at": utc_now_iso(),
        "run_id": summary.get("run_id"),
        "policy": {
            "min_time_reduction_percent": effective_policy.min_time_reduction_percent,
            "require_bug_or_coverage": effective_policy.require_bug_or_coverage,
        },
        "summary": summary,
        "gate_verdict": gate,
        "first_iteration": first_iter_metrics,
        "time_to_first_meaningful_properties_min": time_to_first_min,
        "bug_or_coverage_achieved": bug_or_coverage,
        "baseline_study": baseline_eval,
        "meets_time_reduction_target": time_reduction_meets,
        "overall_success": _overall_success(
            bug_or_coverage=bug_or_coverage,
            time_reduction_meets=time_reduction_meets,
            policy=effective_policy,
        ),
    }

    out = run_dir / "report" / "kpi.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    write_json(out, report)
    report["output"] = str(out)
    return report


def evaluate_baseline_study(path: Path) -> dict[str, Any]:
    path = path.resolve()
    if not path.exists():
        raise FileNotFoundError(path)

    reductions: list[float] = []
    samples = 0
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            b = _parse_float(row.get("baseline_minutes_to_first_meaningful_properties"))
            p = _parse_float(row.get("formalchip_minutes_to_first_meaningful_properties"))
            if b is None or p is None or b <= 0:
                continue
            samples += 1
            reductions.append(((b - p) / b) * 100.0)

    avg = sum(reductions) / len(reductions) if reductions else None
    return {
        "path": str(path),
        "samples": samples,
        "avg_reduction_percent": round(avg, 3) if avg is not None else None,
        "reductions_percent": [round(x, 3) for x in reductions],
    }


def _first_iteration_property_metrics(state: dict[str, Any]) -> dict[str, Any]:
    iterations = list(state.get("iterations", []))
    if not iterations:
        return {
            "properties_total": 0,
            "properties_meaningful": 0,
            "placeholders": 0,
        }

    first = iterations[0]
    property_file = Path(first.get("property_file", ""))
    if not property_file.exists():
        return {
            "properties_total": 0,
            "properties_meaningful": 0,
            "placeholders": 0,
        }

    text = property_file.read_text(encoding="utf-8", errors="replace")
    total = len(re.findall(r"^property\s+", text, flags=re.MULTILINE))
    placeholders = len(
        [
            line
            for line in text.splitlines()
            if line.strip().startswith("// NOTE:") and "placeholder" in line.lower()
        ]
    )
    meaningful = max(0, total - placeholders)

    return {
        "properties_total": total,
        "properties_meaningful": meaningful,
        "placeholders": placeholders,
    }


def _time_to_first_meaningful_properties_min(state: dict[str, Any]) -> float | None:
    started_at = state.get("started_at")
    if not started_at:
        return None

    try:
        run_start = datetime.fromisoformat(str(started_at))
    except Exception:
        return None

    for item in state.get("iterations", []):
        prop_file = Path(item.get("property_file", ""))
        if not prop_file.exists():
            continue
        metrics = _file_metrics(prop_file)
        if metrics["properties_meaningful"] <= 0:
            continue

        completed = item.get("completed_at")
        if not completed:
            continue
        try:
            done = datetime.fromisoformat(str(completed))
        except Exception:
            continue
        mins = (done - run_start).total_seconds() / 60.0
        return round(max(0.0, mins), 3)

    return None


def _file_metrics(path: Path) -> dict[str, int]:
    text = path.read_text(encoding="utf-8", errors="replace")
    total = len(re.findall(r"^property\s+", text, flags=re.MULTILINE))
    placeholders = len(
        [
            line
            for line in text.splitlines()
            if line.strip().startswith("// NOTE:") and "placeholder" in line.lower()
        ]
    )
    return {
        "properties_total": total,
        "properties_meaningful": max(0, total - placeholders),
        "placeholders": placeholders,
    }


def _parse_float(value: str | None) -> float | None:
    if value is None:
        return None
    v = value.strip()
    if not v:
        return None
    try:
        return float(v)
    except ValueError:
        return None


def _overall_success(bug_or_coverage: bool, time_reduction_meets: bool | None, policy: KPIConfig) -> bool:
    if policy.require_bug_or_coverage and not bug_or_coverage:
        return False
    if time_reduction_meets is None:
        return bug_or_coverage if policy.require_bug_or_coverage else True
    return time_reduction_meets and (bug_or_coverage if policy.require_bug_or_coverage else True)


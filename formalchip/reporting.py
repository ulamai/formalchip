from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .config import KPIConfig
from .run_state import RunState
from .util import utc_now_iso, write_json


def summarize_state_dict(state: dict[str, Any]) -> dict[str, Any]:
    iterations = list(state.get("iterations", []))
    failed_names: set[str] = set()
    counterexample_count = 0
    unsat_count = 0
    coverage_hits = 0
    artifact_count = 0
    total_duration_s = 0.0

    for item in iterations:
        failed_names.update(item.get("failed_properties", []))
        counterexample_count += len(item.get("counterexamples", []))
        unsat_count += len(item.get("unsat_cores", []))
        coverage_hits += int(item.get("coverage_hits", 0) or 0)
        artifact_count += len(item.get("artifact_files", []))
        total_duration_s += float(item.get("duration_s", 0.0) or 0.0)

    bug_found = len(failed_names) > 0 or counterexample_count > 0

    return {
        "generated_at": utc_now_iso(),
        "run_id": state.get("run_id"),
        "status": state.get("status"),
        "started_at": state.get("started_at"),
        "completed_at": state.get("completed_at"),
        "iterations": len(iterations),
        "total_duration_s": round(total_duration_s, 3),
        "failed_property_count": len(failed_names),
        "counterexample_lines": counterexample_count,
        "unsat_hints": unsat_count,
        "coverage_hits": coverage_hits,
        "artifact_files": artifact_count,
        "bug_found": bug_found,
        "evidence_pack": state.get("evidence_pack"),
    }


def _state_to_dict(state: RunState) -> dict[str, Any]:
    return {
        "run_id": state.run_id,
        "started_at": state.started_at,
        "completed_at": state.completed_at,
        "status": state.status,
        "config_path": state.config_path,
        "evidence_pack": state.evidence_pack,
        "iterations": [
            {
                "iteration": it.iteration,
                "property_file": it.property_file,
                "engine_log": it.engine_log,
                "started_at": it.started_at,
                "completed_at": it.completed_at,
                "duration_s": it.duration_s,
                "status": it.status,
                "summary": it.summary,
                "failed_properties": it.failed_properties,
                "counterexamples": it.counterexamples,
                "unsat_cores": it.unsat_cores,
                "coverage_hits": it.coverage_hits,
                "artifact_files": it.artifact_files,
            }
            for it in state.iterations
        ],
    }


def build_gate_verdict(summary: dict[str, Any], kpi: KPIConfig | None = None) -> dict[str, Any]:
    policy = kpi or KPIConfig()
    has_bug_or_cov = bool(summary.get("bug_found")) or int(summary.get("coverage_hits", 0) or 0) > 0
    checks = {
        "evidence_pack_present": bool(summary.get("evidence_pack")),
        "has_bug_or_coverage": has_bug_or_cov if policy.require_bug_or_coverage else True,
        "run_completed": summary.get("status") in {"pass", "fail", "unknown"},
    }
    passed = all(checks.values())
    return {
        "generated_at": utc_now_iso(),
        "run_id": summary.get("run_id"),
        "passed": passed,
        "checks": checks,
        "policy": {
            "require_bug_or_coverage": policy.require_bug_or_coverage,
            "min_time_reduction_percent": policy.min_time_reduction_percent,
        },
        "summary_ref": {
            "status": summary.get("status"),
            "coverage_hits": summary.get("coverage_hits"),
            "failed_property_count": summary.get("failed_property_count"),
            "counterexample_lines": summary.get("counterexample_lines"),
        },
    }


def write_run_report(run_dir: Path, state: RunState, kpi: KPIConfig | None = None) -> tuple[Path, Path, Path]:
    run_dir = run_dir.resolve()
    report_dir = run_dir / "report"
    report_dir.mkdir(parents=True, exist_ok=True)

    state_dict = _state_to_dict(state)
    summary = summarize_state_dict(state_dict)
    gate = build_gate_verdict(summary, kpi=kpi)

    json_path = report_dir / "summary.json"
    md_path = report_dir / "summary.md"
    gate_path = report_dir / "gate_verdict.json"

    write_json(json_path, summary)
    write_json(gate_path, gate)
    md_path.write_text(_render_markdown(summary, state_dict, gate), encoding="utf-8")
    return json_path, md_path, gate_path


def load_report(run_dir: Path) -> dict[str, Any]:
    run_dir = run_dir.resolve()
    summary_path = run_dir / "report" / "summary.json"
    if summary_path.exists():
        return json.loads(summary_path.read_text(encoding="utf-8"))

    state_path = run_dir / "state.json"
    if not state_path.exists():
        raise FileNotFoundError(f"No report/summary.json or state.json found under {run_dir}")
    state = json.loads(state_path.read_text(encoding="utf-8"))
    summary = summarize_state_dict(state)
    write_json(summary_path, summary)
    return summary


def load_gate_verdict(run_dir: Path) -> dict[str, Any]:
    run_dir = run_dir.resolve()
    gate_path = run_dir / "report" / "gate_verdict.json"
    if not gate_path.exists():
        summary = load_report(run_dir)
        gate = build_gate_verdict(summary)
        write_json(gate_path, gate)
        return gate
    return json.loads(gate_path.read_text(encoding="utf-8"))


def _render_markdown(summary: dict[str, Any], state: dict[str, Any], gate: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# FormalChip Run Summary")
    lines.append("")
    lines.append(f"- Run ID: `{summary.get('run_id')}`")
    lines.append(f"- Status: `{summary.get('status')}`")
    lines.append(f"- Iterations: `{summary.get('iterations')}`")
    lines.append(f"- Duration (s): `{summary.get('total_duration_s')}`")
    lines.append(f"- Failed Properties (unique): `{summary.get('failed_property_count')}`")
    lines.append(f"- Counterexample Lines: `{summary.get('counterexample_lines')}`")
    lines.append(f"- Coverage Hits: `{summary.get('coverage_hits')}`")
    lines.append(f"- Artifact Files: `{summary.get('artifact_files')}`")
    lines.append("")

    lines.append("## Gate Verdict")
    lines.append("")
    lines.append(f"- Passed: `{gate.get('passed')}`")
    for key, value in gate.get("checks", {}).items():
        lines.append(f"- `{key}`: `{value}`")
    lines.append("")

    lines.append("## Iterations")
    lines.append("")
    lines.append("| Iter | Status | Duration (s) | Coverage Hits | Summary |")
    lines.append("| --- | --- | --- | --- | --- |")
    for item in state.get("iterations", []):
        iter_id = item.get("iteration")
        status = item.get("status")
        duration = item.get("duration_s", 0.0)
        cov = item.get("coverage_hits", 0)
        summary_text = str(item.get("summary", "")).replace("|", "\\|")
        lines.append(f"| {iter_id} | {status} | {duration} | {cov} | {summary_text} |")
    lines.append("")

    evidence_pack = summary.get("evidence_pack")
    if evidence_pack:
        lines.append(f"Evidence pack: `{evidence_pack}`")

    return "\n".join(lines) + "\n"


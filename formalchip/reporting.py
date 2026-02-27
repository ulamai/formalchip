from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .run_state import RunState
from .util import utc_now_iso, write_json


def summarize_state_dict(state: dict[str, Any]) -> dict[str, Any]:
    iterations = list(state.get("iterations", []))
    failed_names: set[str] = set()
    counterexample_count = 0
    unsat_count = 0

    for item in iterations:
        failed_names.update(item.get("failed_properties", []))
        counterexample_count += len(item.get("counterexamples", []))
        unsat_count += len(item.get("unsat_cores", []))

    return {
        "generated_at": utc_now_iso(),
        "run_id": state.get("run_id"),
        "status": state.get("status"),
        "started_at": state.get("started_at"),
        "completed_at": state.get("completed_at"),
        "iterations": len(iterations),
        "failed_property_count": len(failed_names),
        "counterexample_lines": counterexample_count,
        "unsat_hints": unsat_count,
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
                "status": it.status,
                "summary": it.summary,
                "failed_properties": it.failed_properties,
                "counterexamples": it.counterexamples,
                "unsat_cores": it.unsat_cores,
            }
            for it in state.iterations
        ],
    }


def write_run_report(run_dir: Path, state: RunState) -> tuple[Path, Path]:
    run_dir = run_dir.resolve()
    report_dir = run_dir / "report"
    report_dir.mkdir(parents=True, exist_ok=True)

    state_dict = _state_to_dict(state)
    summary = summarize_state_dict(state_dict)

    json_path = report_dir / "summary.json"
    md_path = report_dir / "summary.md"

    write_json(json_path, summary)
    md_path.write_text(_render_markdown(summary, state_dict), encoding="utf-8")
    return json_path, md_path


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


def _render_markdown(summary: dict[str, Any], state: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# FormalChip Run Summary")
    lines.append("")
    lines.append(f"- Run ID: `{summary.get('run_id')}`")
    lines.append(f"- Status: `{summary.get('status')}`")
    lines.append(f"- Iterations: `{summary.get('iterations')}`")
    lines.append(f"- Failed Properties (unique): `{summary.get('failed_property_count')}`")
    lines.append(f"- Counterexample Lines: `{summary.get('counterexample_lines')}`")
    lines.append(f"- Unsat Hints: `{summary.get('unsat_hints')}`")
    lines.append("")

    lines.append("## Iterations")
    lines.append("")
    lines.append("| Iter | Status | Summary |")
    lines.append("| --- | --- | --- |")
    for item in state.get("iterations", []):
        iter_id = item.get("iteration")
        status = item.get("status")
        summary_text = str(item.get("summary", "")).replace("|", "\\|")
        lines.append(f"| {iter_id} | {status} | {summary_text} |")
    lines.append("")

    evidence_pack = summary.get("evidence_pack")
    if evidence_pack:
        lines.append(f"Evidence pack: `{evidence_pack}`")

    return "\n".join(lines) + "\n"


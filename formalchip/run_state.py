from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .util import append_jsonl, ensure_dir, utc_now_iso, write_json


@dataclass
class IterationRecord:
    iteration: int
    property_file: str
    engine_log: str
    status: str
    summary: str
    failed_properties: list[str] = field(default_factory=list)
    counterexamples: list[str] = field(default_factory=list)
    unsat_cores: list[str] = field(default_factory=list)


@dataclass
class RunState:
    run_id: str
    started_at: str
    config_path: str
    status: str = "running"
    completed_at: str | None = None
    iterations: list[IterationRecord] = field(default_factory=list)
    evidence_pack: str | None = None
    reports: dict[str, str] = field(default_factory=dict)


class RunRecorder:
    def __init__(self, run_dir: Path, state: RunState) -> None:
        self.run_dir = run_dir
        self.state_path = run_dir / "state.json"
        self.trace_path = run_dir / "trace.jsonl"
        self.state = state
        ensure_dir(run_dir)

    def save_state(self) -> None:
        write_json(
            self.state_path,
            {
                "run_id": self.state.run_id,
                "started_at": self.state.started_at,
                "completed_at": self.state.completed_at,
                "status": self.state.status,
                "config_path": self.state.config_path,
                "evidence_pack": self.state.evidence_pack,
                "reports": self.state.reports,
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
                    for it in self.state.iterations
                ],
            },
        )

    def trace(self, event: str, payload: dict[str, Any] | None = None) -> None:
        append_jsonl(
            self.trace_path,
            {
                "timestamp": utc_now_iso(),
                "event": event,
                "payload": payload or {},
            },
        )

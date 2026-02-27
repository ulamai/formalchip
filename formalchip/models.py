from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

Status = Literal["pass", "fail", "unknown", "error"]


@dataclass
class SpecClause:
    """A normalized verification intent extracted from any spec artifact."""

    clause_id: str
    text: str
    source: str
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class PropertyCandidate:
    """Generated property unit that can be serialized into an SVA file."""

    prop_id: str
    name: str
    body: str
    kind: Literal["assert", "assume", "cover"] = "assert"
    source_clause: str | None = None
    notes: str | None = None


@dataclass
class IterationFeedback:
    """Normalized feedback from formal tools."""

    status: Status
    summary: str
    failed_properties: list[str] = field(default_factory=list)
    counterexamples: list[str] = field(default_factory=list)
    unsat_cores: list[str] = field(default_factory=list)


@dataclass
class FormalResult:
    """Result returned by an engine adapter."""

    status: Status
    summary: str
    log_path: Path
    failed_properties: list[str] = field(default_factory=list)
    counterexamples: list[str] = field(default_factory=list)
    unsat_cores: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RunContext:
    """Derived context for each loop iteration."""

    run_id: str
    run_dir: Path
    iteration: int
    rtl_files: list[Path]
    top_module: str
    clock: str
    reset: str
    reset_active_low: bool


from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from formalchip.models import FormalResult, PropertyCandidate, RunContext


@dataclass
class EngineRunInput:
    context: RunContext
    candidate_file: Path
    candidates: list[PropertyCandidate]
    iteration_dir: Path


class FormalEngine(Protocol):
    name: str

    def tool_version(self) -> str:
        ...

    def run(self, run_input: EngineRunInput) -> FormalResult:
        ...


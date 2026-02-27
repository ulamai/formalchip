from __future__ import annotations

from pathlib import Path

from formalchip.models import FormalResult
from formalchip.parsers import parse_generic_log

from .base import EngineRunInput


class MockEngine:
    name = "mock"

    def __init__(self, pass_after: int = 1) -> None:
        self.pass_after = max(1, pass_after)

    def tool_version(self) -> str:
        return "mock-engine/1.0"

    def run(self, run_input: EngineRunInput) -> FormalResult:
        log_path = run_input.iteration_dir / "mock.log"
        names = [c.name for c in run_input.candidates[:3]]

        if run_input.context.iteration < self.pass_after:
            lines = [
                "STATUS: FAILED",
                f"assertion {names[0] if names else 'p0'} failed",
                "counterexample: req=1 ack=0 for 4 cycles",
            ]
        else:
            lines = [
                "STATUS: PASSED",
                "all properties proven",
            ]
        log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        result = parse_generic_log(log_path)
        result.metadata["engine"] = self.name
        return result


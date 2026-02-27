from __future__ import annotations

import json
import re
import shlex
import subprocess
from dataclasses import asdict
from typing import Protocol

from .config import LibraryPattern, LLMConfig
from .models import IterationFeedback, PropertyCandidate, SpecClause
from .synthesis import SynthesisInputs, synthesize_candidates


class LLMBackend(Protocol):
    def propose(
        self,
        clauses: list[SpecClause],
        libraries: list[LibraryPattern],
        synthesis_inputs: SynthesisInputs,
    ) -> list[PropertyCandidate]:
        ...

    def repair(
        self,
        current: list[PropertyCandidate],
        feedback: IterationFeedback,
        clauses: list[SpecClause],
        libraries: list[LibraryPattern],
        synthesis_inputs: SynthesisInputs,
    ) -> list[PropertyCandidate]:
        ...


class DeterministicLLM:
    """Template-backed fallback that emulates proposal/repair behavior deterministically."""

    def propose(
        self,
        clauses: list[SpecClause],
        libraries: list[LibraryPattern],
        synthesis_inputs: SynthesisInputs,
    ) -> list[PropertyCandidate]:
        return synthesize_candidates(clauses, libraries, synthesis_inputs)

    def repair(
        self,
        current: list[PropertyCandidate],
        feedback: IterationFeedback,
        clauses: list[SpecClause],
        libraries: list[LibraryPattern],
        synthesis_inputs: SynthesisInputs,
    ) -> list[PropertyCandidate]:
        if not current:
            return self.propose(clauses, libraries, synthesis_inputs)

        failed = set(feedback.failed_properties)
        out: list[PropertyCandidate] = []
        for prop in current:
            clone = PropertyCandidate(**asdict(prop))
            if clone.name in failed:
                clone.body = _repair_body(clone.body)
                clone.notes = (
                    (clone.notes + " | ") if clone.notes else ""
                ) + f"Auto-repaired after feedback: {feedback.summary}"
            out.append(clone)

        if failed:
            out.append(
                PropertyCandidate(
                    prop_id=f"repair_assume_{len(out)+1}",
                    name=f"repair_assume_reset_stable_{len(out)+1}",
                    kind="assume",
                    body=f"@(posedge {synthesis_inputs.clock}) $changed({synthesis_inputs.reset}) |-> ##1 $stable({synthesis_inputs.reset});",
                    notes="Constrains pathological reset oscillation seen in CEX",
                )
            )
        return out


def _repair_body(body: str) -> str:
    # Expand bounded eventuality windows when they fail quickly.
    m = re.search(r"##\[0:(\d+)\]", body)
    if m:
        old = int(m.group(1))
        return body.replace(f"##[0:{old}]", f"##[0:{old + 2}]")

    # Relax strict next-cycle implication into bounded eventuality.
    if "|=>" in body:
        return body.replace("|=>", "|-> ##[0:1]")

    return body


class CommandLLM:
    """Pluggable command backend for external LLM integration."""

    def __init__(self, command: str) -> None:
        self.command = command

    def propose(
        self,
        clauses: list[SpecClause],
        libraries: list[LibraryPattern],
        synthesis_inputs: SynthesisInputs,
    ) -> list[PropertyCandidate]:
        payload = {
            "mode": "propose",
            "clauses": [asdict(c) for c in clauses],
            "libraries": [asdict(l) for l in libraries],
            "synthesis_inputs": _serialize_synthesis_inputs(synthesis_inputs),
        }
        return self._call(payload)

    def repair(
        self,
        current: list[PropertyCandidate],
        feedback: IterationFeedback,
        clauses: list[SpecClause],
        libraries: list[LibraryPattern],
        synthesis_inputs: SynthesisInputs,
    ) -> list[PropertyCandidate]:
        payload = {
            "mode": "repair",
            "current": [asdict(c) for c in current],
            "feedback": asdict(feedback),
            "clauses": [asdict(c) for c in clauses],
            "libraries": [asdict(l) for l in libraries],
            "synthesis_inputs": _serialize_synthesis_inputs(synthesis_inputs),
        }
        return self._call(payload)

    def _call(self, payload: dict) -> list[PropertyCandidate]:
        argv = shlex.split(self.command)
        proc = subprocess.run(
            argv,
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            check=False,
        )
        if proc.returncode != 0:
            raise RuntimeError(f"LLM command failed: {proc.stderr.strip()}")

        try:
            obj = json.loads(proc.stdout)
        except json.JSONDecodeError as exc:
            raise RuntimeError("LLM command did not emit valid JSON") from exc

        raw_candidates = obj.get("candidates", [])
        out: list[PropertyCandidate] = []
        for raw in raw_candidates:
            out.append(PropertyCandidate(**raw))
        return out


def make_llm_backend(cfg: LLMConfig) -> LLMBackend:
    backend = cfg.backend.lower().strip()
    if backend == "deterministic":
        return DeterministicLLM()
    if backend == "command":
        if not cfg.command:
            raise ValueError("llm.command must be set when backend=command")
        return CommandLLM(cfg.command)
    raise ValueError(f"Unsupported llm backend: {cfg.backend}")


def _serialize_synthesis_inputs(inputs: SynthesisInputs) -> dict:
    return {
        "clock": inputs.clock,
        "reset": inputs.reset,
        "reset_active_low": inputs.reset_active_low,
        "known_signals": sorted(inputs.known_signals),
    }

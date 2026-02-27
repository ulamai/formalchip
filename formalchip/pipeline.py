from __future__ import annotations

from dataclasses import dataclass

from .config import FormalChipConfig, LibraryPattern
from .llm import make_llm_backend
from .models import PropertyCandidate, SpecClause
from .rtl import collect_signals
from .spec_ingest import load_spec_clauses
from .synthesis import SynthesisInputs, optimize_candidates, synthesize_candidates


@dataclass
class InitialSynthesis:
    clauses: list[SpecClause]
    libraries: list[LibraryPattern]
    candidates: list[PropertyCandidate]
    inputs: SynthesisInputs


def build_initial_synthesis(config: FormalChipConfig, force_deterministic: bool = False) -> InitialSynthesis:
    clauses = load_spec_clauses(config.specs)
    libraries = _libraries_with_constraints(config)

    known_signals = collect_signals(config.project.rtl_files)
    known_signals.add(config.project.clock)
    known_signals.add(config.project.reset)

    inputs = SynthesisInputs(
        clock=config.project.clock,
        reset=config.project.reset,
        reset_active_low=config.project.reset_active_low,
        known_signals=known_signals,
        signal_aliases=config.project.signal_aliases,
    )

    if force_deterministic:
        candidates = synthesize_candidates(clauses, libraries, inputs)
    else:
        llm = make_llm_backend(config.llm)
        candidates = llm.propose(clauses=clauses, libraries=libraries, synthesis_inputs=inputs)
    candidates = optimize_candidates(candidates)

    return InitialSynthesis(clauses=clauses, libraries=libraries, candidates=candidates, inputs=inputs)


def _libraries_with_constraints(config: FormalChipConfig) -> list[LibraryPattern]:
    out = list(config.libraries)
    for item in config.constraints.assumptions:
        out.append(
            LibraryPattern(
                kind="inline",
                options={
                    "name": item.name,
                    "expr": item.expr,
                    "when": item.when or "",
                    "property_kind": "assume",
                    "note": item.note or "Structured environment assumption",
                },
            )
        )
    for item in config.constraints.covers:
        out.append(
            LibraryPattern(
                kind="inline",
                options={
                    "name": item.name,
                    "expr": item.expr,
                    "when": item.when or "",
                    "property_kind": "cover",
                    "note": item.note or "Structured coverage objective",
                },
            )
        )
    return out

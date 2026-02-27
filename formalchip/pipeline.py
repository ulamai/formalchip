from __future__ import annotations

from dataclasses import dataclass

from .config import FormalChipConfig
from .llm import make_llm_backend
from .models import PropertyCandidate, SpecClause
from .rtl import collect_signals
from .spec_ingest import load_spec_clauses
from .synthesis import SynthesisInputs, synthesize_candidates


@dataclass
class InitialSynthesis:
    clauses: list[SpecClause]
    candidates: list[PropertyCandidate]
    inputs: SynthesisInputs


def build_initial_synthesis(config: FormalChipConfig, force_deterministic: bool = False) -> InitialSynthesis:
    clauses = load_spec_clauses(config.specs)

    known_signals = collect_signals(config.project.rtl_files)
    known_signals.add(config.project.clock)
    known_signals.add(config.project.reset)

    inputs = SynthesisInputs(
        clock=config.project.clock,
        reset=config.project.reset,
        reset_active_low=config.project.reset_active_low,
        known_signals=known_signals,
    )

    if force_deterministic:
        candidates = synthesize_candidates(clauses, config.libraries, inputs)
    else:
        llm = make_llm_backend(config.llm)
        candidates = llm.propose(clauses=clauses, libraries=config.libraries, synthesis_inputs=inputs)

    return InitialSynthesis(clauses=clauses, candidates=candidates, inputs=inputs)


from __future__ import annotations

import random
from pathlib import Path

from .config import FormalChipConfig
from .engines import make_engine
from .engines.base import EngineRunInput
from .evidence import build_evidence_pack
from .llm import make_llm_backend
from .models import IterationFeedback, RunContext
from .pipeline import build_initial_synthesis
from .reporting import write_run_report
from .run_state import IterationRecord, RunRecorder, RunState
from .synthesis import write_candidate_file
from .util import ensure_dir, utc_now_iso


def _new_run_id(project_name: str) -> str:
    safe = "".join(ch if ch.isalnum() else "-" for ch in project_name.lower()).strip("-") or "run"
    stamp = utc_now_iso().replace("+00:00", "Z").replace("-", "").replace(":", "")
    suffix = random.randint(1000, 9999)
    return f"{safe}-{stamp}-{suffix}"


def run_formalchip(config: FormalChipConfig, max_iterations_override: int | None = None) -> RunState:
    run_id = _new_run_id(config.project.name)
    run_dir = ensure_dir(config.loop.workdir / run_id)

    max_iters = max_iterations_override or config.loop.max_iterations
    state = RunState(
        run_id=run_id,
        started_at=utc_now_iso(),
        config_path=str(config.config_path),
    )
    recorder = RunRecorder(run_dir=run_dir, state=state)
    recorder.save_state()

    # Store a verbatim config snapshot for reproducibility.
    snapshot = run_dir / f"config.snapshot{config.config_path.suffix or '.toml'}"
    snapshot.write_text(config.config_path.read_text(encoding="utf-8"), encoding="utf-8")

    recorder.trace(
        "run_started",
        {
            "run_id": run_id,
            "project": config.project.name,
            "max_iterations": max_iters,
            "engine": config.engine.kind,
            "llm_backend": config.llm.backend,
        },
    )

    init = build_initial_synthesis(config)
    clauses = init.clauses
    synthesis_inputs = init.inputs
    recorder.trace("clauses_loaded", {"count": len(clauses)})
    recorder.trace("rtl_introspection", {"signal_count": len(synthesis_inputs.known_signals)})

    llm = make_llm_backend(config.llm)
    engine = make_engine(config.engine)
    tool_versions = {engine.name: engine.tool_version()}

    candidates = init.candidates
    recorder.trace("initial_candidates", {"count": len(candidates)})

    final_status = "fail"
    for iteration in range(1, max_iters + 1):
        iter_dir = ensure_dir(run_dir / f"iter_{iteration:02d}")
        property_file = iter_dir / "properties.sv"
        write_candidate_file(property_file, candidates)

        context = RunContext(
            run_id=run_id,
            run_dir=run_dir,
            iteration=iteration,
            rtl_files=config.project.rtl_files,
            top_module=config.project.top_module,
            clock=config.project.clock,
            reset=config.project.reset,
            reset_active_low=config.project.reset_active_low,
        )

        recorder.trace(
            "iteration_started",
            {
                "iteration": iteration,
                "properties": len(candidates),
                "property_file": str(property_file),
            },
        )

        result = engine.run(
            EngineRunInput(
                context=context,
                candidate_file=property_file,
                candidates=candidates,
                iteration_dir=iter_dir,
            )
        )

        state.iterations.append(
            IterationRecord(
                iteration=iteration,
                property_file=str(property_file),
                engine_log=str(result.log_path),
                status=result.status,
                summary=result.summary,
                failed_properties=result.failed_properties,
                counterexamples=result.counterexamples,
                unsat_cores=result.unsat_cores,
            )
        )
        recorder.trace(
            "iteration_finished",
            {
                "iteration": iteration,
                "status": result.status,
                "summary": result.summary,
                "failed_properties": result.failed_properties,
            },
        )
        recorder.save_state()

        if result.status == "pass":
            final_status = "pass"
            break
        if result.status == "error":
            final_status = "error"
            break

        feedback = IterationFeedback(
            status=result.status,
            summary=result.summary,
            failed_properties=result.failed_properties,
            counterexamples=result.counterexamples,
            unsat_cores=result.unsat_cores,
        )
        candidates = llm.repair(
            current=candidates,
            feedback=feedback,
            clauses=clauses,
            libraries=config.libraries,
            synthesis_inputs=synthesis_inputs,
        )
        recorder.trace("candidates_repaired", {"iteration": iteration, "count": len(candidates)})

    state.status = final_status
    state.completed_at = utc_now_iso()

    evidence_output = run_dir / "evidence" / f"formalchip-evidence-{run_id}.tar.gz"
    state.evidence_pack = str(evidence_output.resolve())

    report_json, report_md = write_run_report(run_dir, state)
    state.reports = {"json": str(report_json), "markdown": str(report_md)}

    evidence_path = build_evidence_pack(
        run_dir=run_dir,
        config_path=config.config_path,
        tool_versions=tool_versions,
        output_path=evidence_output,
    )
    state.evidence_pack = str(evidence_path)

    recorder.trace(
        "run_completed",
        {
            "status": state.status,
            "iterations": len(state.iterations),
            "evidence_pack": state.evidence_pack,
        },
    )
    recorder.save_state()
    return state

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .config import FormalChipConfig
from .pipeline import build_initial_synthesis
from .synthesis import is_placeholder_candidate, supported_library_kinds
from .util import which_or_none


@dataclass
class DoctorReport:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    infos: list[str] = field(default_factory=list)
    candidate_count: int = 0
    placeholder_count: int = 0

    @property
    def ok(self) -> bool:
        return not self.errors


def run_doctor(config: FormalChipConfig) -> DoctorReport:
    report = DoctorReport()

    if not config.project.rtl_files:
        report.errors.append("[project].rtl_files is empty")

    missing_rtl = [str(p) for p in config.project.rtl_files if not p.exists()]
    if missing_rtl:
        report.errors.append(f"Missing RTL files: {', '.join(missing_rtl)}")

    missing_specs = [str(s.path) for s in config.specs if not s.path.exists()]
    if missing_specs:
        report.errors.append(f"Missing spec files: {', '.join(missing_specs)}")

    top_ok = False
    if not missing_rtl:
        mod_pat = re.compile(rf"\bmodule\s+{re.escape(config.project.top_module)}\b")
        for rtl in config.project.rtl_files:
            try:
                txt = rtl.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            if mod_pat.search(txt):
                top_ok = True
                break
        if not top_ok:
            report.warnings.append(
                f"Top module `{config.project.top_module}` was not found by simple scan in provided RTL files."
            )

    report.infos.append(f"engine={config.engine.kind}")
    report.infos.append(f"llm_backend={config.llm.backend}")
    report.infos.append(f"constraints_assumptions={len(config.constraints.assumptions)}")
    report.infos.append(f"constraints_covers={len(config.constraints.covers)}")

    kind = config.engine.kind.lower().strip()
    if kind == "symbiyosys":
        cmd = config.engine.command or "sby"
        if which_or_none(cmd) is None:
            report.errors.append(f"SymbiYosys command not found in PATH: {cmd}")
    elif kind in {"vcformal", "jasper", "questa"}:
        if not config.engine.command:
            report.errors.append(f"engine.command is required for kind={kind}")
        else:
            exe = config.engine.command.split()[0]
            if which_or_none(exe) is None:
                report.warnings.append(
                    f"Command executable for engine `{kind}` not found in PATH: {exe}"
                )

    if config.llm.backend.lower().strip() == "command" and not config.llm.command:
        report.errors.append("llm.command is required when llm.backend=command")

    known_libs = supported_library_kinds()
    unknown_libs = sorted({lib.kind for lib in config.libraries if lib.kind.lower() not in known_libs})
    if unknown_libs:
        report.warnings.append(f"Unknown library kinds (ignored by synthesis): {', '.join(unknown_libs)}")

    if report.errors:
        return report

    try:
        init = build_initial_synthesis(config, force_deterministic=True)
        report.candidate_count = len(init.candidates)
        report.placeholder_count = sum(1 for c in init.candidates if is_placeholder_candidate(c))

        report.infos.append(f"loaded_clauses={len(init.clauses)}")
        report.infos.append(f"known_signals={len(init.inputs.known_signals)}")
        report.infos.append(f"generated_candidates={report.candidate_count}")

        if config.project.clock not in init.inputs.known_signals:
            report.warnings.append(f"Clock `{config.project.clock}` not found in RTL signal scan")
        if config.project.reset not in init.inputs.known_signals:
            report.warnings.append(f"Reset `{config.project.reset}` not found in RTL signal scan")

        if report.placeholder_count > 0:
            report.warnings.append(
                f"Generated {report.placeholder_count}/{report.candidate_count} placeholder properties."
            )
        if report.candidate_count > 0:
            ratio = report.placeholder_count / report.candidate_count
            if ratio >= 0.3:
                report.warnings.append(
                    "Placeholder ratio is high; add signal aliases, structured constraints, or inline properties."
                )
        if report.candidate_count == 0:
            report.errors.append("No properties were generated from specs/libraries.")
    except Exception as exc:
        report.errors.append(f"Synthesis preflight failed: {exc}")

    return report


def format_doctor_report(report: DoctorReport) -> str:
    lines: list[str] = []
    lines.append("Doctor report")
    lines.append(f"ok={str(report.ok).lower()}")
    lines.append(f"errors={len(report.errors)} warnings={len(report.warnings)}")
    if report.candidate_count:
        lines.append(f"candidates={report.candidate_count} placeholders={report.placeholder_count}")

    if report.infos:
        lines.append("[info]")
        lines.extend(f"- {msg}" for msg in report.infos)

    if report.warnings:
        lines.append("[warnings]")
        lines.extend(f"- {msg}" for msg in report.warnings)

    if report.errors:
        lines.append("[errors]")
        lines.extend(f"- {msg}" for msg in report.errors)

    return "\n".join(lines)

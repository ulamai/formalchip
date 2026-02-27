from __future__ import annotations

import re
from pathlib import Path

from .models import FormalResult


FAIL_NAME_PATTERNS = [
    re.compile(r"assert(?:ion)?\s+([a-zA-Z_][a-zA-Z0-9_]*)\s+failed", re.IGNORECASE),
    re.compile(r"property\s+([a-zA-Z_][a-zA-Z0-9_]*)\s+failed", re.IGNORECASE),
    re.compile(r"failed\s+property\s*[:=]\s*([a-zA-Z_][a-zA-Z0-9_]*)", re.IGNORECASE),
    re.compile(r"Assert failed in\s+([a-zA-Z_][a-zA-Z0-9_]*)", re.IGNORECASE),
    re.compile(r"assert\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*:\s*FAIL", re.IGNORECASE),
]


def parse_symbiyosys_log(log_path: Path) -> FormalResult:
    text = log_path.read_text(encoding="utf-8", errors="replace")

    status = _detect_status(text)
    failed = sorted(set(_collect_failed_names(text)))
    cex = _collect_counterexample_lines(text)
    unsat = _collect_unsat_lines(text)
    coverage_hits = _count_coverage_hits(text)

    summary = _summarize(status, failed, cex, unsat)
    return FormalResult(
        status=status,  # type: ignore[arg-type]
        summary=summary,
        log_path=log_path,
        failed_properties=failed,
        counterexamples=cex,
        unsat_cores=unsat,
        coverage_hits=coverage_hits,
    )


def parse_generic_log(log_path: Path) -> FormalResult:
    text = log_path.read_text(encoding="utf-8", errors="replace")

    status = _detect_status(text)
    failed = sorted(set(_collect_failed_names(text)))
    cex = _collect_counterexample_lines(text)
    unsat = _collect_unsat_lines(text)
    coverage_hits = _count_coverage_hits(text)

    return FormalResult(
        status=status,  # type: ignore[arg-type]
        summary=_summarize(status, failed, cex, unsat),
        log_path=log_path,
        failed_properties=failed,
        counterexamples=cex,
        unsat_cores=unsat,
        coverage_hits=coverage_hits,
    )


def _detect_status(text: str) -> str:
    lower = text.lower()

    # Highest priority first.
    if any(tok in lower for tok in ["status: error", " done (error", "\nerror:", "sby error"]):
        return "error"
    if any(tok in lower for tok in ["status: failed", " done (fail", "counterexample", "assert failed"]):
        return "fail"
    if any(tok in lower for tok in ["status: passed", " done (pass", "all properties proven", "success"]):
        return "pass"
    if "status: unknown" in lower or " done (unknown" in lower:
        return "unknown"

    # Conservative fallback.
    if "error" in lower:
        return "error"
    if "fail" in lower:
        return "fail"
    if "pass" in lower:
        return "pass"
    return "unknown"


def _collect_failed_names(text: str) -> list[str]:
    out: list[str] = []
    for pat in FAIL_NAME_PATTERNS:
        for m in pat.finditer(text):
            out.append(m.group(1))
    return out


def _collect_counterexample_lines(text: str) -> list[str]:
    out: list[str] = []
    for line in text.splitlines():
        lo = line.lower()
        if "counterexample" in lo or "trace" in lo or "witness" in lo:
            out.append(line.strip())
    return out[:30]


def _collect_unsat_lines(text: str) -> list[str]:
    out: list[str] = []
    for line in text.splitlines():
        lo = line.lower()
        if "unsat" in lo or "core" in lo:
            out.append(line.strip())
    return out[:30]


def _count_coverage_hits(text: str) -> int:
    count = 0
    for line in text.splitlines():
        lo = line.lower()
        if "cover" in lo and any(k in lo for k in ["reached", "passed", "triggered", "hit"]):
            count += 1
    return count


def _summarize(status: str, failed: list[str], cex: list[str], unsat: list[str]) -> str:
    pieces = [f"status={status}"]
    if failed:
        pieces.append(f"failed={len(failed)}")
    if cex:
        pieces.append(f"counterexamples={len(cex)}")
    if unsat:
        pieces.append(f"unsat_hints={len(unsat)}")
    return ", ".join(pieces)

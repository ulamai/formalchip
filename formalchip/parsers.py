from __future__ import annotations

import re
from pathlib import Path

from .models import FormalResult


FAIL_NAME_PATTERNS = [
    re.compile(r"assert(?:ion)?\s+([a-zA-Z_][a-zA-Z0-9_]*)\s+failed", re.IGNORECASE),
    re.compile(r"property\s+([a-zA-Z_][a-zA-Z0-9_]*)\s+failed", re.IGNORECASE),
    re.compile(r"failed\s+property\s*[:=]\s*([a-zA-Z_][a-zA-Z0-9_]*)", re.IGNORECASE),
]


def parse_symbiyosys_log(log_path: Path) -> FormalResult:
    text = log_path.read_text(encoding="utf-8", errors="replace")
    lower = text.lower()

    status = "unknown"
    if "status: passed" in lower or re.search(r"\bpass\b", lower):
        status = "pass"
    if "status: failed" in lower or re.search(r"\bfail\b", lower):
        status = "fail"
    if "error" in lower and status == "unknown":
        status = "error"

    failed: list[str] = []
    for pat in FAIL_NAME_PATTERNS:
        for m in pat.finditer(text):
            failed.append(m.group(1))
    failed = sorted(set(failed))

    cex = _collect_counterexample_lines(text)
    unsat = _collect_unsat_lines(text)

    summary = _summarize(status, failed, cex, unsat)
    return FormalResult(
        status=status,  # type: ignore[arg-type]
        summary=summary,
        log_path=log_path,
        failed_properties=failed,
        counterexamples=cex,
        unsat_cores=unsat,
    )


def parse_generic_log(log_path: Path) -> FormalResult:
    text = log_path.read_text(encoding="utf-8", errors="replace")
    lower = text.lower()
    status = "unknown"
    if any(tok in lower for tok in [" pass", "passed", "success"]):
        status = "pass"
    if any(tok in lower for tok in [" fail", "failed", "counterexample"]):
        status = "fail"
    if "error" in lower and status == "unknown":
        status = "error"

    failed = sorted(set(_collect_failed_names(text)))
    cex = _collect_counterexample_lines(text)
    unsat = _collect_unsat_lines(text)

    return FormalResult(
        status=status,  # type: ignore[arg-type]
        summary=_summarize(status, failed, cex, unsat),
        log_path=log_path,
        failed_properties=failed,
        counterexamples=cex,
        unsat_cores=unsat,
    )


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
        if "counterexample" in lo or "trace" in lo:
            out.append(line.strip())
    return out[:20]


def _collect_unsat_lines(text: str) -> list[str]:
    out: list[str] = []
    for line in text.splitlines():
        lo = line.lower()
        if "unsat" in lo or "core" in lo:
            out.append(line.strip())
    return out[:20]


def _summarize(status: str, failed: list[str], cex: list[str], unsat: list[str]) -> str:
    pieces = [f"status={status}"]
    if failed:
        pieces.append(f"failed={len(failed)}")
    if cex:
        pieces.append(f"counterexamples={len(cex)}")
    if unsat:
        pieces.append(f"unsat_hints={len(unsat)}")
    return ", ".join(pieces)


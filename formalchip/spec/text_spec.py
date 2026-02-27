from __future__ import annotations

from pathlib import Path
from typing import Any

from formalchip.models import SpecClause


def parse_text_spec(path: Path, options: dict[str, Any] | None = None) -> list[SpecClause]:
    _ = options
    clauses: list[SpecClause] = []
    lines = path.read_text(encoding="utf-8").splitlines()
    counter = 0
    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#"):
            continue
        if line.startswith("-"):
            line = line[1:].strip()
        counter += 1
        cid = f"text_{counter:03d}"
        clauses.append(
            SpecClause(
                clause_id=cid,
                text=line,
                source=str(path),
                tags=["text"],
            )
        )
    return clauses

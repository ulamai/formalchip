from __future__ import annotations

import csv
from pathlib import Path

from formalchip.models import SpecClause


def parse_register_csv(path: Path) -> list[SpecClause]:
    clauses: list[SpecClause] = []
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        idx = 0
        for row in reader:
            idx += 1
            name = (row.get("name") or row.get("register") or "reg").strip()
            reset = (row.get("reset") or row.get("reset_value") or "0").strip()
            access = (row.get("access") or row.get("sw_access") or "rw").strip().lower()
            width = (row.get("width") or row.get("bits") or "32").strip()

            clauses.append(
                SpecClause(
                    clause_id=f"reg_{idx:03d}_reset",
                    text=f"Register {name} resets to {reset}.",
                    source=str(path),
                    tags=["register", "reset"],
                    metadata={"register": name, "reset": reset, "access": access, "width": width},
                )
            )
            if access in {"ro", "read-only", "r"}:
                clauses.append(
                    SpecClause(
                        clause_id=f"reg_{idx:03d}_ro",
                        text=f"Register {name} is read-only from software interface.",
                        source=str(path),
                        tags=["register", "access", "read_only"],
                        metadata={"register": name, "access": access},
                    )
                )
    return clauses


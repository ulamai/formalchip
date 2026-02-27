from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from formalchip.models import SpecClause


def parse_rule_table_csv(path: Path, options: dict[str, Any] | None = None) -> list[SpecClause]:
    _ = options
    clauses: list[SpecClause] = []
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        idx = 0
        for row in reader:
            idx += 1
            rule_id = (row.get("rule_id") or f"rule_{idx}").strip()
            condition = (row.get("condition") or row.get("if") or "").strip()
            guarantee = (row.get("guarantee") or row.get("then") or "").strip()
            text = f"If {condition}, then {guarantee}." if condition else guarantee
            clauses.append(
                SpecClause(
                    clause_id=f"tbl_{rule_id}",
                    text=text,
                    source=str(path),
                    tags=["rule_table"],
                    metadata={"condition": condition, "guarantee": guarantee, "rule_id": rule_id},
                )
            )
    return clauses

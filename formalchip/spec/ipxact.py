from __future__ import annotations

from pathlib import Path
from typing import Any
import xml.etree.ElementTree as ET

from formalchip.models import SpecClause


def _find_text(node: ET.Element, suffix: str) -> str | None:
    for child in node.iter():
        if child.tag.endswith(suffix):
            if child.text is not None:
                return child.text.strip()
    return None


def parse_ipxact(path: Path, options: dict[str, Any] | None = None) -> list[SpecClause]:
    _ = options
    tree = ET.parse(path)
    root = tree.getroot()

    regs = [elem for elem in root.iter() if elem.tag.endswith("register")]
    clauses: list[SpecClause] = []
    for idx, reg in enumerate(regs, 1):
        name = _find_text(reg, "name") or f"reg_{idx}"
        reset = _find_text(reg, "value") or "0"
        clauses.append(
            SpecClause(
                clause_id=f"ipxact_{idx:03d}_reset",
                text=f"Register {name} resets to {reset}.",
                source=str(path),
                tags=["ipxact", "register", "reset"],
                metadata={"register": name, "reset": reset},
            )
        )
    return clauses

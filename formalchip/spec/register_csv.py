from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from formalchip.models import SpecClause


def _parse_int(value: str | None) -> int | None:
    if value is None:
        return None
    v = value.strip().lower()
    if not v:
        return None
    try:
        if v.startswith("0x"):
            return int(v, 16)
        return int(v, 10)
    except ValueError:
        return None


def _render_signal(template: str, name: str) -> str:
    return template.format(name=name, name_lower=name.lower(), name_upper=name.upper())


def parse_register_csv(path: Path, options: dict[str, Any] | None = None) -> list[SpecClause]:
    options = options or {}
    signal_template = str(options.get("signal_template", "{name_lower}_q"))
    sw_we_signal = options.get("sw_we_signal")
    sw_addr_signal = options.get("sw_addr_signal")
    sw_addr_width = int(options.get("sw_addr_width", 32))

    clauses: list[SpecClause] = []
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        idx = 0
        for row in reader:
            idx += 1
            name = (row.get("name") or row.get("register") or "reg").strip()
            address = (row.get("address") or row.get("addr") or "").strip()
            reset = (row.get("reset") or row.get("reset_value") or "0").strip()
            access = (row.get("access") or row.get("sw_access") or "rw").strip().lower()
            width = (row.get("width") or row.get("bits") or "32").strip()
            signal = _render_signal(signal_template, name)
            address_int = _parse_int(address)

            clauses.append(
                SpecClause(
                    clause_id=f"reg_{idx:03d}_reset",
                    text=f"Register {name} resets to {reset}.",
                    source=str(path),
                    tags=["register", "reset"],
                    metadata={
                        "register": name,
                        "address": address,
                        "address_int": address_int,
                        "reset": reset,
                        "access": access,
                        "width": width,
                        "signal": signal,
                        "sw_we_signal": sw_we_signal,
                        "sw_addr_signal": sw_addr_signal,
                        "sw_addr_width": sw_addr_width,
                    },
                )
            )
            if access in {"ro", "read-only", "r"}:
                clauses.append(
                    SpecClause(
                        clause_id=f"reg_{idx:03d}_ro",
                        text=f"Register {name} is read-only from software interface.",
                        source=str(path),
                        tags=["register", "access", "read_only"],
                        metadata={
                            "register": name,
                            "address": address,
                            "address_int": address_int,
                            "signal": signal,
                            "access": access,
                            "sw_we_signal": sw_we_signal,
                            "sw_addr_signal": sw_addr_signal,
                            "sw_addr_width": sw_addr_width,
                        },
                    )
                )
    return clauses

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from .config import LibraryPattern
from .models import PropertyCandidate, SpecClause


_IDENTIFIER_RE = re.compile(r"[^a-zA-Z0-9_]+")
_TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_SV_KEYWORDS = {
    "if",
    "else",
    "begin",
    "end",
    "disable",
    "iff",
    "posedge",
    "negedge",
    "property",
    "assert",
    "assume",
    "cover",
    "and",
    "or",
    "not",
    "true",
    "false",
}

SUPPORTED_LIBRARY_KINDS = {
    "handshake",
    "fifo_safety",
    "reset_sequence",
    "inline",
}


@dataclass
class SynthesisInputs:
    clock: str
    reset: str
    reset_active_low: bool
    known_signals: set[str] = field(default_factory=set)


def supported_library_kinds() -> set[str]:
    return set(SUPPORTED_LIBRARY_KINDS)


def _sanitize_id(value: str) -> str:
    out = _IDENTIFIER_RE.sub("_", value).strip("_")
    if not out:
        return "unnamed"
    if out[0].isdigit():
        out = f"p_{out}"
    return out.lower()


def _reset_disable(reset: str, active_low: bool) -> str:
    return f"disable iff(!{reset})" if active_low else f"disable iff({reset})"


def _reset_asserted(reset: str, active_low: bool) -> str:
    return f"!{reset}" if active_low else reset


def _const_sv(value: str, width: int = 32) -> str:
    v = value.strip().lower()
    if v.startswith("0x"):
        return f"{width}'h{v[2:]}"
    if v.isdigit():
        return f"{width}'d{v}"
    if "'" in v:
        return value
    return value


def _mk_property(
    prop_id: str,
    name: str,
    body: str,
    kind: Literal["assert", "assume", "cover"] = "assert",
    source_clause: str | None = None,
    notes: str | None = None,
) -> PropertyCandidate:
    return PropertyCandidate(
        prop_id=prop_id,
        name=_sanitize_id(name),
        body=body,
        kind=kind,
        source_clause=source_clause,
        notes=notes,
    )


def _mk_assert(prop_id: str, name: str, body: str, source_clause: str | None = None, notes: str | None = None) -> PropertyCandidate:
    return _mk_property(prop_id=prop_id, name=name, body=body, kind="assert", source_clause=source_clause, notes=notes)


def _placeholder_body(clock: str, reset: str, active_low: bool) -> str:
    return f"@({clocking(clock)}) {_reset_disable(reset, active_low)} 1'b1 |-> 1'b1;"


def _missing_signals(required: list[str], known_signals: set[str]) -> list[str]:
    if not known_signals:
        return []
    return [sig for sig in required if sig not in known_signals]


def _fallback_assert(
    clause: SpecClause,
    name: str,
    clock: str,
    reset: str,
    active_low: bool,
    reason: str,
) -> PropertyCandidate:
    return _mk_assert(
        clause.clause_id,
        name,
        _placeholder_body(clock, reset, active_low),
        source_clause=clause.clause_id,
        notes=reason,
    )


def _extract_identifiers(expr: str) -> list[str]:
    out: list[str] = []
    for tok in _TOKEN_RE.findall(expr):
        low = tok.lower()
        if low in _SV_KEYWORDS:
            continue
        out.append(tok)
    return out


def _text_clause_to_candidates(clause: SpecClause, inputs: SynthesisInputs) -> list[PropertyCandidate]:
    text = clause.text.strip()
    lower = text.lower()
    disable = _reset_disable(inputs.reset, inputs.reset_active_low)

    # Pattern: "if a then b next cycle"
    m = re.search(r"if\s+([a-zA-Z_][a-zA-Z0-9_]*)\s+then\s+([a-zA-Z_][a-zA-Z0-9_]*)\s+next\s+cycle", lower)
    if m:
        cond, cons = m.group(1), m.group(2)
        missing = _missing_signals([cond, cons], inputs.known_signals)
        if missing:
            return [
                _fallback_assert(
                    clause,
                    f"{clause.clause_id}_placeholder",
                    inputs.clock,
                    inputs.reset,
                    inputs.reset_active_low,
                    f"Signals not found in RTL: {', '.join(missing)}",
                )
            ]
        body = f"@({clocking(inputs.clock)}) {disable} {cond} |=> {cons};"
        return [
            _mk_assert(
                clause.clause_id,
                f"{clause.clause_id}_{cond}_implies_{cons}",
                body,
                source_clause=clause.clause_id,
            )
        ]

    # Pattern: "never a and b"
    m = re.search(r"never\s+([a-zA-Z_][a-zA-Z0-9_]*)\s+and\s+([a-zA-Z_][a-zA-Z0-9_]*)", lower)
    if m:
        a, b = m.group(1), m.group(2)
        missing = _missing_signals([a, b], inputs.known_signals)
        if missing:
            return [
                _fallback_assert(
                    clause,
                    f"{clause.clause_id}_placeholder",
                    inputs.clock,
                    inputs.reset,
                    inputs.reset_active_low,
                    f"Signals not found in RTL: {', '.join(missing)}",
                )
            ]
        body = f"@({clocking(inputs.clock)}) {disable} !({a} && {b});"
        return [
            _mk_assert(
                clause.clause_id,
                f"{clause.clause_id}_never_{a}_{b}",
                body,
                source_clause=clause.clause_id,
            )
        ]

    # Pattern: "within N cycles" handshake-ish clause.
    m = re.search(
        r"([a-zA-Z_][a-zA-Z0-9_]*)\s+.*within\s+(\d+)\s+cycles\s+.*([a-zA-Z_][a-zA-Z0-9_]*)",
        lower,
    )
    if m:
        req, bound, ack = m.group(1), int(m.group(2)), m.group(3)
        missing = _missing_signals([req, ack], inputs.known_signals)
        if missing:
            return [
                _fallback_assert(
                    clause,
                    f"{clause.clause_id}_placeholder",
                    inputs.clock,
                    inputs.reset,
                    inputs.reset_active_low,
                    f"Signals not found in RTL: {', '.join(missing)}",
                )
            ]
        body = f"@({clocking(inputs.clock)}) {disable} {req} |-> ##[0:{bound}] {ack};"
        return [
            _mk_assert(
                clause.clause_id,
                f"{clause.clause_id}_{req}_to_{ack}_{bound}",
                body,
                source_clause=clause.clause_id,
            )
        ]

    # Pattern: "x should be low/high right after reset"
    m = re.search(
        r"([a-zA-Z_][a-zA-Z0-9_]*)\s+should\s+be\s+(low|high)\s+right\s+after\s+reset",
        lower,
    )
    if m:
        sig, level = m.group(1), m.group(2)
        missing = _missing_signals([sig], inputs.known_signals)
        if missing:
            return [
                _fallback_assert(
                    clause,
                    f"{clause.clause_id}_placeholder",
                    inputs.clock,
                    inputs.reset,
                    inputs.reset_active_low,
                    f"Signals not found in RTL: {', '.join(missing)}",
                )
            ]

        expected = "1'b0" if level == "low" else "1'b1"
        reset_expr = _reset_asserted(inputs.reset, inputs.reset_active_low)
        body = f"@({clocking(inputs.clock)}) {reset_expr} |=> ({sig} == {expected});"
        return [
            _mk_assert(
                clause.clause_id,
                f"{clause.clause_id}_{sig}_reset_{level}",
                body,
                source_clause=clause.clause_id,
            )
        ]

    return [
        _fallback_assert(
            clause,
            f"{clause.clause_id}_placeholder",
            inputs.clock,
            inputs.reset,
            inputs.reset_active_low,
            f"Unable to derive strict logic from clause: {text}",
        )
    ]


def _register_clause_to_candidates(clause: SpecClause, inputs: SynthesisInputs) -> list[PropertyCandidate]:
    md = clause.metadata
    reg = str(md.get("register", "reg")).strip()
    width = int(str(md.get("width", "32")) or "32")
    reg_sig = str(md.get("signal") or f"{_sanitize_id(reg)}_q")
    candidates: list[PropertyCandidate] = []

    if "reset" in clause.tags:
        reset_value = str(md.get("reset", "0"))
        missing = _missing_signals([reg_sig], inputs.known_signals)
        if missing:
            candidates.append(
                _fallback_assert(
                    clause,
                    f"{clause.clause_id}_{reg_sig}_reset_placeholder",
                    inputs.clock,
                    inputs.reset,
                    inputs.reset_active_low,
                    f"Register signal mapping missing: {', '.join(missing)}",
                )
            )
        else:
            reset_expr = _reset_asserted(inputs.reset, inputs.reset_active_low)
            body = f"@({clocking(inputs.clock)}) {reset_expr} |=> {reg_sig} == {_const_sv(reset_value, width)};"
            candidates.append(
                _mk_assert(
                    clause.clause_id,
                    f"{clause.clause_id}_{reg_sig}_reset",
                    body,
                    source_clause=clause.clause_id,
                )
            )

    if "read_only" in clause.tags:
        sw_we_signal = md.get("sw_we_signal")
        sw_addr_signal = md.get("sw_addr_signal")
        sw_addr_width = int(md.get("sw_addr_width", 32))
        address = md.get("address")

        if not (sw_we_signal and sw_addr_signal and address):
            candidates.append(
                _fallback_assert(
                    clause,
                    f"{clause.clause_id}_{reg_sig}_ro_placeholder",
                    inputs.clock,
                    inputs.reset,
                    inputs.reset_active_low,
                    "Read-only check requires sw_we_signal, sw_addr_signal, and register address mapping.",
                )
            )
        else:
            required = [str(sw_we_signal), str(sw_addr_signal), reg_sig]
            missing = _missing_signals(required, inputs.known_signals)
            if missing:
                candidates.append(
                    _fallback_assert(
                        clause,
                        f"{clause.clause_id}_{reg_sig}_ro_placeholder",
                        inputs.clock,
                        inputs.reset,
                        inputs.reset_active_low,
                        f"Read-only mapping references unknown signals: {', '.join(missing)}",
                    )
                )
            else:
                addr_const = _const_sv(str(address), sw_addr_width)
                body = (
                    f"@({clocking(inputs.clock)}) {_reset_disable(inputs.reset, inputs.reset_active_low)} "
                    f"({sw_we_signal} && ({sw_addr_signal} == {addr_const})) |-> $stable({reg_sig});"
                )
                candidates.append(
                    _mk_assert(
                        clause.clause_id,
                        f"{clause.clause_id}_{reg_sig}_ro",
                        body,
                        source_clause=clause.clause_id,
                    )
                )

    return candidates


def _rule_table_clause_to_candidates(clause: SpecClause, inputs: SynthesisInputs) -> list[PropertyCandidate]:
    condition = str(clause.metadata.get("condition", "")).strip()
    guarantee = str(clause.metadata.get("guarantee", "")).strip()
    disable = _reset_disable(inputs.reset, inputs.reset_active_low)

    if not condition or not guarantee:
        body = _placeholder_body(inputs.clock, inputs.reset, inputs.reset_active_low)
        note = "Rule row missing condition or guarantee"
    else:
        required = _extract_identifiers(condition) + _extract_identifiers(guarantee)
        missing = _missing_signals(sorted(set(required)), inputs.known_signals)
        if missing:
            body = _placeholder_body(inputs.clock, inputs.reset, inputs.reset_active_low)
            note = f"Rule references unknown signals: {', '.join(missing)}"
        else:
            body = f"@({clocking(inputs.clock)}) {disable} ({condition}) |-> ({guarantee});"
            note = None

    return [
        _mk_assert(
            clause.clause_id,
            f"{clause.clause_id}_rule",
            body,
            source_clause=clause.clause_id,
            notes=note,
        )
    ]


def _inline_library_candidate(pattern: LibraryPattern, inputs: SynthesisInputs) -> list[PropertyCandidate]:
    o = pattern.options
    expr = str(o.get("expr", "")).strip()
    if not expr:
        return [
            _mk_assert(
                "lib_inline",
                str(o.get("name", "lib_inline_placeholder")),
                _placeholder_body(inputs.clock, inputs.reset, inputs.reset_active_low),
                notes="Inline property requires `expr`",
            )
        ]

    when = str(o.get("when", "")).strip()
    required = _extract_identifiers(expr)
    if when:
        required += _extract_identifiers(when)

    missing = _missing_signals(sorted(set(required)), inputs.known_signals)
    if missing:
        return [
            _mk_assert(
                "lib_inline",
                str(o.get("name", "lib_inline_placeholder")),
                _placeholder_body(inputs.clock, inputs.reset, inputs.reset_active_low),
                notes=f"Inline property references unknown signals: {', '.join(missing)}",
            )
        ]

    disable = _reset_disable(inputs.reset, inputs.reset_active_low)
    if when:
        body = f"@({clocking(inputs.clock)}) {disable} ({when}) |-> ({expr});"
    else:
        body = f"@({clocking(inputs.clock)}) {disable} ({expr});"

    raw_kind = str(o.get("property_kind", "assert")).strip().lower()
    kind: Literal["assert", "assume", "cover"]
    if raw_kind in {"assert", "assume", "cover"}:
        kind = raw_kind  # type: ignore[assignment]
    else:
        kind = "assert"

    return [
        _mk_property(
            prop_id=str(o.get("id", "lib_inline")),
            name=str(o.get("name", "lib_inline")),
            body=body,
            kind=kind,
            notes=o.get("note"),
        )
    ]


def _library_candidates(pattern: LibraryPattern, inputs: SynthesisInputs) -> list[PropertyCandidate]:
    disable = _reset_disable(inputs.reset, inputs.reset_active_low)
    kind = pattern.kind.lower()
    o = pattern.options
    candidates: list[PropertyCandidate] = []

    if kind == "handshake":
        req = str(o.get("req", "req"))
        ack = str(o.get("ack", "ack"))
        bound = int(o.get("bound", 8))
        missing = _missing_signals([req, ack], inputs.known_signals)
        if missing:
            candidates.append(
                _mk_assert(
                    f"lib_hs_{req}_{ack}",
                    f"lib_hs_{req}_{ack}_placeholder",
                    _placeholder_body(inputs.clock, inputs.reset, inputs.reset_active_low),
                    notes=f"Handshake mapping missing signals: {', '.join(missing)}",
                )
            )
        else:
            candidates.append(
                _mk_assert(
                    f"lib_hs_{req}_{ack}",
                    f"lib_hs_{req}_{ack}_eventual",
                    f"@({clocking(inputs.clock)}) {disable} {req} |-> ##[0:{bound}] {ack};",
                    notes="Reusable handshake liveness/safety intent",
                )
            )

    elif kind == "fifo_safety":
        full = str(o.get("full", "fifo_full"))
        empty = str(o.get("empty", "fifo_empty"))
        push = str(o.get("push", "fifo_push"))
        pop = str(o.get("pop", "fifo_pop"))

        missing = _missing_signals([full, empty, push, pop], inputs.known_signals)
        if missing:
            candidates.append(
                _mk_assert(
                    "lib_fifo_safety",
                    "lib_fifo_safety_placeholder",
                    _placeholder_body(inputs.clock, inputs.reset, inputs.reset_active_low),
                    notes=f"FIFO mapping missing signals: {', '.join(missing)}",
                )
            )
        else:
            candidates.append(
                _mk_assert(
                    "lib_fifo_overflow",
                    "lib_fifo_no_overflow",
                    f"@({clocking(inputs.clock)}) {disable} !({full} && {push});",
                    notes="Prevent push when FIFO is full",
                )
            )
            candidates.append(
                _mk_assert(
                    "lib_fifo_underflow",
                    "lib_fifo_no_underflow",
                    f"@({clocking(inputs.clock)}) {disable} !({empty} && {pop});",
                    notes="Prevent pop when FIFO is empty",
                )
            )

    elif kind == "reset_sequence":
        signal = str(o.get("signal", "valid"))
        value = str(o.get("value", "0"))
        latency = int(o.get("latency", 1))

        missing = _missing_signals([signal], inputs.known_signals)
        if missing:
            candidates.append(
                _mk_assert(
                    f"lib_rst_{signal}",
                    f"lib_reset_seq_{signal}_placeholder",
                    _placeholder_body(inputs.clock, inputs.reset, inputs.reset_active_low),
                    notes=f"Reset-sequence signal missing: {', '.join(missing)}",
                )
            )
        else:
            reset_asserted = _reset_asserted(inputs.reset, inputs.reset_active_low)
            candidates.append(
                _mk_assert(
                    f"lib_rst_{signal}",
                    f"lib_reset_seq_{signal}",
                    f"@({clocking(inputs.clock)}) {reset_asserted} |=> ##[{latency}:{latency}] ({signal} == {value});",
                    notes="Reset sequencing rule",
                )
            )

    elif kind == "inline":
        candidates.extend(_inline_library_candidate(pattern, inputs))

    return candidates


def clocking(clock: str) -> str:
    return f"posedge {clock}"


def synthesize_candidates(
    clauses: list[SpecClause],
    libraries: list[LibraryPattern],
    inputs: SynthesisInputs,
) -> list[PropertyCandidate]:
    out: list[PropertyCandidate] = []
    seen_names: set[str] = set()

    for clause in clauses:
        if "register" in clause.tags or "ipxact" in clause.tags:
            props = _register_clause_to_candidates(clause, inputs)
        elif "rule_table" in clause.tags:
            props = _rule_table_clause_to_candidates(clause, inputs)
        else:
            props = _text_clause_to_candidates(clause, inputs)

        for prop in props:
            name = prop.name
            i = 2
            while name in seen_names:
                name = f"{prop.name}_{i}"
                i += 1
            prop.name = name
            seen_names.add(name)
            out.append(prop)

    for lib in libraries:
        for prop in _library_candidates(lib, inputs):
            name = prop.name
            i = 2
            while name in seen_names:
                name = f"{prop.name}_{i}"
                i += 1
            prop.name = name
            seen_names.add(name)
            out.append(prop)

    return out


def serialize_sva(candidates: list[PropertyCandidate]) -> str:
    lines: list[str] = []
    lines.append("`ifdef FORMAL")
    lines.append("")
    for c in candidates:
        lines.append(f"// FC_ID: {c.prop_id}")
        if c.source_clause:
            lines.append(f"// SOURCE: {c.source_clause}")
        if c.notes:
            lines.append(f"// NOTE: {c.notes}")
        lines.append(f"property {c.name};")
        lines.append(f"  {c.body}")
        lines.append("endproperty")
        lines.append(f"{c.kind} property ({c.name});")
        lines.append("")
    lines.append("`endif")
    lines.append("")
    return "\n".join(lines)


def write_candidate_file(path: Path, candidates: list[PropertyCandidate]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(serialize_sva(candidates), encoding="utf-8")


def is_placeholder_candidate(candidate: PropertyCandidate) -> bool:
    note = (candidate.notes or "").lower()
    if "placeholder" in note:
        return True
    return "1'b1 |-> 1'b1" in candidate.body

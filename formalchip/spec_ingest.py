from __future__ import annotations

from formalchip.config import SpecInput
from formalchip.models import SpecClause
from formalchip.spec import parse_ipxact, parse_register_csv, parse_rule_table_csv, parse_text_spec


SUPPORTED_SPEC_KINDS = {
    "text": parse_text_spec,
    "register_csv": parse_register_csv,
    "ipxact": parse_ipxact,
    "rule_table_csv": parse_rule_table_csv,
}


def load_spec_clauses(specs: list[SpecInput]) -> list[SpecClause]:
    out: list[SpecClause] = []
    for spec in specs:
        fn = SUPPORTED_SPEC_KINDS.get(spec.kind)
        if fn is None:
            raise ValueError(f"Unsupported spec kind: {spec.kind}")
        out.extend(fn(spec.path))
    return out


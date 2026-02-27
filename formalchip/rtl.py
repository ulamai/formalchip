from __future__ import annotations

import re
from pathlib import Path


DECL_RE = re.compile(
    r"\b(?:input|output|inout|wire|logic|reg)\b(?:\s+(?:signed|unsigned))?(?:\s*\[[^\]]+\])?\s+([^;]+);",
    re.IGNORECASE,
)
IDENT_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
DECL_KEYWORDS = {"input", "output", "inout", "wire", "logic", "reg", "signed", "unsigned"}


def collect_signals(rtl_files: list[Path]) -> set[str]:
    """
    Collect a best-effort set of declared signal names from RTL files.
    This is intentionally lightweight to avoid parser dependencies.
    """
    out: set[str] = set()
    for path in rtl_files:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        # Strip one-line comments to reduce false positives.
        text = re.sub(r"//.*$", "", text, flags=re.MULTILINE)
        for m in DECL_RE.finditer(text):
            names = m.group(1)
            for part in names.split(","):
                part = re.sub(r"\[[^\]]+\]", " ", part)
                tokens = [tok for tok in IDENT_RE.findall(part) if tok.lower() not in DECL_KEYWORDS]
                if tokens:
                    out.add(tokens[-1])
    return out

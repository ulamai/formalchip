from __future__ import annotations

from pathlib import Path


_TEMPLATE_ROOT = Path(__file__).resolve().parent / "templates" / "engines"


def supported_engine_templates() -> list[str]:
    out: list[str] = []
    if not _TEMPLATE_ROOT.exists():
        return out
    for p in sorted(_TEMPLATE_ROOT.iterdir()):
        if p.is_dir():
            out.append(p.name)
    return out


def export_engine_template(engine: str, output_path: Path) -> Path:
    engine = engine.lower().strip()
    src = _TEMPLATE_ROOT / engine / "run.tcl"
    if not src.exists():
        supported = ", ".join(supported_engine_templates())
        raise ValueError(f"No template for engine '{engine}'. Supported: {supported}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    return output_path


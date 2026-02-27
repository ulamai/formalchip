from __future__ import annotations

import shutil
from pathlib import Path

from formalchip.models import FormalResult
from formalchip.parsers import parse_symbiyosys_log
from formalchip.util import run_command, which_or_none

from .base import EngineRunInput


class SymbiYosysEngine:
    name = "symbiyosys"

    def __init__(self, command: str | None = None, sby_file: Path | None = None, timeout_s: int = 600) -> None:
        self.command = command or "sby"
        self.sby_file = sby_file
        self.timeout_s = timeout_s

    def tool_version(self) -> str:
        exe = which_or_none(self.command)
        if not exe:
            return f"{self.command}:not-found"
        rc, out, err = run_command([self.command, "--version"], timeout_s=30)
        if rc == 0:
            v = (out or err).strip().splitlines()
            return v[0] if v else f"{self.command}:ok"
        return f"{self.command}:version-error"

    def run(self, run_input: EngineRunInput) -> FormalResult:
        iter_dir = run_input.iteration_dir
        sby_path = iter_dir / "run.sby"
        log_path = iter_dir / "engine.log"

        if self.sby_file is not None:
            template = self.sby_file.read_text(encoding="utf-8")
            rendered = _render_sby(
                template=template,
                top=run_input.context.top_module,
                property_file=run_input.candidate_file,
                rtl_files=run_input.context.rtl_files,
            )
        else:
            rendered = _default_sby(
                top=run_input.context.top_module,
                property_file=run_input.candidate_file,
                rtl_files=run_input.context.rtl_files,
            )
        sby_path.write_text(rendered, encoding="utf-8")

        rc, out, err = run_command(
            [self.command, "-f", str(sby_path)],
            cwd=iter_dir,
            timeout_s=self.timeout_s,
        )
        log_path.write_text(out + ("\n" if out else "") + err, encoding="utf-8")

        result = parse_symbiyosys_log(log_path)
        artifact_files = _collect_sby_artifacts(iter_dir)
        result.artifact_files = artifact_files
        result.metadata.update({"engine": self.name, "returncode": rc, "sby": str(sby_path)})
        result.metadata["artifact_count"] = len(artifact_files)
        if rc != 0 and result.status == "unknown":
            result.status = "error"
            result.summary = f"status=error, returncode={rc}"
        return result


def _render_sby(template: str, top: str, property_file: Path, rtl_files: list[Path]) -> str:
    rendered = template
    rendered = rendered.replace("{{TOP_MODULE}}", top)
    rendered = rendered.replace("{{PROPERTY_FILE}}", str(property_file))
    rendered = rendered.replace("{{RTL_FILES}}", "\n".join(str(p) for p in rtl_files))
    return rendered


def _default_sby(top: str, property_file: Path, rtl_files: list[Path]) -> str:
    files = [str(p) for p in rtl_files] + [str(property_file)]
    script_reads = "\n".join(f"read -formal {f}" for f in files)
    files_lines = "\n".join(files)
    return f"""[options]
mode prove
depth 20

[engines]
smtbmc

[script]
{script_reads}
prep -top {top}

[files]
{files_lines}
"""


def _collect_sby_artifacts(iter_dir: Path) -> list[str]:
    """
    Collect witness-like artifacts into a stable path under artifacts/witnesses.
    Returns paths relative to iteration directory.
    """
    keep_ext = {".vcd", ".yw", ".aiw", ".cex", ".json", ".smtc", ".txt"}
    src_files: list[Path] = []
    for path in iter_dir.rglob("*"):
        if path.is_dir():
            continue
        if path.name in {"engine.log", "run.sby", "properties.sv"}:
            continue
        if path.suffix.lower() in keep_ext or "trace" in path.name.lower() or "witness" in path.name.lower():
            src_files.append(path)

    if not src_files:
        return []

    dst_root = iter_dir / "artifacts" / "witnesses"
    dst_root.mkdir(parents=True, exist_ok=True)
    out: list[str] = []
    for src in sorted(src_files):
        rel = src.relative_to(iter_dir)
        # Preserve subpaths while avoiding collisions.
        dst = dst_root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.resolve() != dst.resolve():
            shutil.copy2(src, dst)
        out.append(str(dst.relative_to(iter_dir)))
    return out

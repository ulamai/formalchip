from __future__ import annotations

import json
import tarfile
from pathlib import Path
from typing import Any

from .util import gather_runtime_facts, sha256_file, utc_now_iso, write_json


def build_evidence_pack(
    run_dir: Path,
    config_path: Path,
    tool_versions: dict[str, str],
    output_path: Path | None = None,
) -> Path:
    run_dir = run_dir.resolve()
    evidence_dir = run_dir / "evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)

    manifest = _build_manifest(run_dir=run_dir, config_path=config_path, tool_versions=tool_versions)
    manifest_path = evidence_dir / "manifest.json"
    write_json(manifest_path, manifest)

    run_id = run_dir.name
    out = output_path or (evidence_dir / f"formalchip-evidence-{run_id}.tar.gz")
    out = out.resolve()

    with tarfile.open(out, "w:gz") as tar:
        for path in sorted(run_dir.rglob("*")):
            if path == out:
                continue
            if path.is_dir():
                continue
            arcname = str(path.relative_to(run_dir))
            tar.add(path, arcname=arcname)

    return out


def _build_manifest(run_dir: Path, config_path: Path, tool_versions: dict[str, str]) -> dict[str, Any]:
    files: list[dict[str, str | int]] = []
    for path in sorted(run_dir.rglob("*")):
        if path.is_dir():
            continue
        rel = str(path.relative_to(run_dir))
        files.append(
            {
                "path": rel,
                "sha256": sha256_file(path),
                "size": path.stat().st_size,
            }
        )

    config_digest = sha256_file(config_path) if config_path.exists() else None
    gate_path = run_dir / "report" / "gate_verdict.json"
    gate_verdict = None
    if gate_path.exists():
        try:
            gate_verdict = json.loads(gate_path.read_text(encoding="utf-8"))
        except Exception:
            gate_verdict = None
    return {
        "generated_at": utc_now_iso(),
        "run_dir": str(run_dir),
        "config_path": str(config_path),
        "config_sha256": config_digest,
        "tool_versions": tool_versions,
        "runtime": gather_runtime_facts(),
        "gate_verdict": gate_verdict,
        "files": files,
    }


def read_state(run_dir: Path) -> dict[str, Any]:
    state_path = run_dir / "state.json"
    if not state_path.exists():
        return {}
    return json.loads(state_path.read_text(encoding="utf-8"))

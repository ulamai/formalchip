from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import tomllib


@dataclass
class ProjectConfig:
    name: str
    rtl_files: list[Path]
    top_module: str
    clock: str = "clk"
    reset: str = "rst_n"
    reset_active_low: bool = True
    signal_aliases: dict[str, str] = field(default_factory=dict)


@dataclass
class LLMConfig:
    backend: str = "deterministic"
    model: str = "formalchip-template-v1"
    command: str | None = None


@dataclass
class EngineConfig:
    kind: str = "mock"
    command: str | None = None
    sby_file: Path | None = None
    timeout_s: int = 600
    pass_after: int = 1


@dataclass
class LoopConfig:
    max_iterations: int = 3
    workdir: Path = Path(".formalchip/runs")


@dataclass
class ConstraintItem:
    name: str
    expr: str
    kind: str
    when: str | None = None
    note: str | None = None


@dataclass
class ConstraintsConfig:
    assumptions: list[ConstraintItem] = field(default_factory=list)
    covers: list[ConstraintItem] = field(default_factory=list)


@dataclass
class KPIConfig:
    min_time_reduction_percent: float = 30.0
    require_bug_or_coverage: bool = True


@dataclass
class SpecInput:
    kind: str
    path: Path
    options: dict[str, Any] = field(default_factory=dict)


@dataclass
class LibraryPattern:
    kind: str
    options: dict[str, Any] = field(default_factory=dict)


@dataclass
class FormalChipConfig:
    config_path: Path
    project: ProjectConfig
    llm: LLMConfig
    engine: EngineConfig
    loop: LoopConfig
    constraints: ConstraintsConfig
    kpi: KPIConfig
    specs: list[SpecInput]
    libraries: list[LibraryPattern]


def _load_raw(path: Path) -> dict[str, Any]:
    if path.suffix == ".toml":
        return tomllib.loads(path.read_text(encoding="utf-8"))
    if path.suffix == ".json":
        return json.loads(path.read_text(encoding="utf-8"))
    if path.suffix in {".yaml", ".yml"}:
        try:
            import yaml  # type: ignore
        except Exception as exc:  # pragma: no cover
            raise RuntimeError(
                "YAML config requested but PyYAML is not installed. Use TOML/JSON or install pyyaml."
            ) from exc
        with path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            if not isinstance(data, dict):
                raise ValueError("Configuration root must be a mapping")
            return data
    raise ValueError(f"Unsupported config extension: {path.suffix}")


def _resolve_path(base: Path, value: str | None) -> Path | None:
    if value is None:
        return None
    p = Path(value)
    if p.is_absolute():
        return p
    return (base / p).resolve()


def _resolve_many(base: Path, values: list[str]) -> list[Path]:
    out: list[Path] = []
    for value in values:
        resolved = _resolve_path(base, value)
        if resolved is not None:
            out.append(resolved)
    return out


def load_config(path: str | Path) -> FormalChipConfig:
    cfg_path = Path(path).resolve()
    raw = _load_raw(cfg_path)
    base = cfg_path.parent

    project_raw = raw.get("project", {})
    if "rtl_files" not in project_raw:
        raise ValueError("[project].rtl_files is required")
    if "top_module" not in project_raw:
        raise ValueError("[project].top_module is required")

    project = ProjectConfig(
        name=project_raw.get("name", "formalchip-project"),
        rtl_files=_resolve_many(base, list(project_raw["rtl_files"])),
        top_module=str(project_raw["top_module"]),
        clock=str(project_raw.get("clock", "clk")),
        reset=str(project_raw.get("reset", "rst_n")),
        reset_active_low=bool(project_raw.get("reset_active_low", True)),
        signal_aliases={str(k): str(v) for k, v in dict(project_raw.get("signal_aliases", {})).items()},
    )

    llm_raw = raw.get("llm", {})
    llm = LLMConfig(
        backend=str(llm_raw.get("backend", "deterministic")),
        model=str(llm_raw.get("model", "formalchip-template-v1")),
        command=llm_raw.get("command"),
    )

    engine_raw = raw.get("engine", {})
    engine = EngineConfig(
        kind=str(engine_raw.get("kind", "mock")),
        command=engine_raw.get("command"),
        sby_file=_resolve_path(base, engine_raw.get("sby_file")),
        timeout_s=int(engine_raw.get("timeout_s", 600)),
        pass_after=int(engine_raw.get("pass_after", 1)),
    )

    loop_raw = raw.get("loop", {})
    loop = LoopConfig(
        max_iterations=int(loop_raw.get("max_iterations", 3)),
        workdir=_resolve_path(base, loop_raw.get("workdir"))
        or (base / ".formalchip" / "runs").resolve(),
    )

    constraints_raw = raw.get("constraints", {})
    if not isinstance(constraints_raw, dict):
        raise ValueError("[constraints] must be a table/object")

    assumptions: list[ConstraintItem] = []
    for idx, item in enumerate(constraints_raw.get("assumptions", [])):
        if not isinstance(item, dict):
            raise ValueError(f"constraints.assumptions[{idx}] must be a table/object")
        expr = str(item.get("expr", "")).strip()
        if not expr:
            raise ValueError(f"constraints.assumptions[{idx}].expr is required")
        assumptions.append(
            ConstraintItem(
                name=str(item.get("name", f"assumption_{idx+1}")),
                expr=expr,
                kind="assume",
                when=str(item.get("when")).strip() if item.get("when") is not None else None,
                note=str(item.get("note")).strip() if item.get("note") is not None else None,
            )
        )

    covers: list[ConstraintItem] = []
    for idx, item in enumerate(constraints_raw.get("covers", [])):
        if not isinstance(item, dict):
            raise ValueError(f"constraints.covers[{idx}] must be a table/object")
        expr = str(item.get("expr", "")).strip()
        if not expr:
            raise ValueError(f"constraints.covers[{idx}].expr is required")
        covers.append(
            ConstraintItem(
                name=str(item.get("name", f"cover_{idx+1}")),
                expr=expr,
                kind="cover",
                when=str(item.get("when")).strip() if item.get("when") is not None else None,
                note=str(item.get("note")).strip() if item.get("note") is not None else None,
            )
        )
    constraints = ConstraintsConfig(assumptions=assumptions, covers=covers)

    kpi_raw = raw.get("kpi", {})
    if not isinstance(kpi_raw, dict):
        raise ValueError("[kpi] must be a table/object")
    kpi = KPIConfig(
        min_time_reduction_percent=float(kpi_raw.get("min_time_reduction_percent", 30.0)),
        require_bug_or_coverage=bool(kpi_raw.get("require_bug_or_coverage", True)),
    )

    specs_raw = raw.get("specs", [])
    specs: list[SpecInput] = []
    for idx, spec in enumerate(specs_raw):
        if not isinstance(spec, dict):
            raise ValueError(f"specs[{idx}] must be a table/object")
        kind = str(spec.get("kind", "text"))
        path_value = spec.get("path")
        if path_value is None:
            raise ValueError(f"specs[{idx}].path is required")
        options = {k: v for k, v in spec.items() if k not in {"kind", "path"}}
        spec_path = _resolve_path(base, str(path_value))
        assert spec_path is not None
        specs.append(SpecInput(kind=kind, path=spec_path, options=options))

    libs_raw = raw.get("libraries", [])
    libraries: list[LibraryPattern] = []
    for idx, lib in enumerate(libs_raw):
        if not isinstance(lib, dict):
            raise ValueError(f"libraries[{idx}] must be a table/object")
        kind = str(lib.get("kind", "unknown"))
        options = {k: v for k, v in lib.items() if k != "kind"}
        libraries.append(LibraryPattern(kind=kind, options=options))

    return FormalChipConfig(
        config_path=cfg_path,
        project=project,
        llm=llm,
        engine=engine,
        loop=loop,
        constraints=constraints,
        kpi=kpi,
        specs=specs,
        libraries=libraries,
    )

from __future__ import annotations

from formalchip.config import EngineConfig

from .mock import MockEngine
from .proprietary import ScriptedEngine
from .symbiyosys import SymbiYosysEngine


def make_engine(cfg: EngineConfig):
    kind = cfg.kind.lower().strip()
    if kind == "mock":
        return MockEngine(pass_after=cfg.pass_after)
    if kind == "symbiyosys":
        return SymbiYosysEngine(command=cfg.command, sby_file=cfg.sby_file, timeout_s=cfg.timeout_s)
    if kind in {"vcformal", "jasper", "questa"}:
        if not cfg.command:
            raise ValueError(f"engine.command is required for kind={kind}")
        return ScriptedEngine(name=kind, command=cfg.command, timeout_s=cfg.timeout_s)
    raise ValueError(f"Unsupported engine kind: {cfg.kind}")


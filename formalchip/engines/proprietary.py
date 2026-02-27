from __future__ import annotations

import os
import shlex
import subprocess
from pathlib import Path

from formalchip.models import FormalResult
from formalchip.parsers import parse_generic_log

from .base import EngineRunInput


class ScriptedEngine:
    def __init__(self, name: str, command: str, timeout_s: int = 1800) -> None:
        self.name = name
        self.command = command
        self.timeout_s = timeout_s

    def tool_version(self) -> str:
        argv = shlex.split(self.command)
        if not argv:
            return f"{self.name}:invalid-command"
        base = argv[0]
        try:
            proc = subprocess.run(
                [base, "--version"],
                capture_output=True,
                text=True,
                check=False,
                timeout=20,
            )
            v = (proc.stdout or proc.stderr).strip().splitlines()
            return v[0] if v else f"{base}:ok"
        except Exception:
            return f"{base}:version-unavailable"

    def run(self, run_input: EngineRunInput) -> FormalResult:
        log_path = run_input.iteration_dir / f"{self.name}.log"
        env = dict(os.environ)
        env["FORMALCHIP_PROPERTY_FILE"] = str(run_input.candidate_file)
        env["FORMALCHIP_TOP"] = run_input.context.top_module
        env["FORMALCHIP_RTL_FILES"] = os.pathsep.join(str(p) for p in run_input.context.rtl_files)

        argv = shlex.split(self.command)
        proc = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            timeout=self.timeout_s,
            check=False,
            cwd=run_input.iteration_dir,
            env=env,
        )
        log_path.write_text(
            (proc.stdout or "") + ("\n" if proc.stdout else "") + (proc.stderr or ""),
            encoding="utf-8",
        )
        result = parse_generic_log(log_path)
        result.metadata.update({"engine": self.name, "returncode": proc.returncode})
        if proc.returncode != 0 and result.status == "unknown":
            result.status = "error"
            result.summary = f"status=error, returncode={proc.returncode}"
        return result



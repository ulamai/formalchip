from __future__ import annotations

from pathlib import Path


def scaffold_open_source_pilot(target: Path) -> None:
    target.mkdir(parents=True, exist_ok=True)
    (target / "rtl").mkdir(parents=True, exist_ok=True)
    (target / "spec").mkdir(parents=True, exist_ok=True)
    (target / "ci").mkdir(parents=True, exist_ok=True)
    (target / "metrics").mkdir(parents=True, exist_ok=True)

    _write_if_missing(
        target / "formalchip.toml",
        """[project]
name = "pilot-fifo-open"
rtl_files = ["rtl/fifo_buggy.sv"]
top_module = "fifo_buggy"
clock = "clk"
reset = "rst_n"
reset_active_low = true
signal_aliases = { request = "req", acknowledge = "ack" }

[llm]
backend = "deterministic"
model = "formalchip-template-v1"

[engine]
kind = "symbiyosys"
command = "sby"
timeout_s = 300

[loop]
max_iterations = 2
workdir = ".formalchip/runs"

[[specs]]
kind = "text"
path = "spec/intent.md"

[[libraries]]
kind = "canonical_10"
req = "req"
ack = "ack"
push = "push"
pop = "pop"
full = "full"
empty = "empty"
level = "level"
level_width = 3
level_max = "4"
valid = "valid"
bound = 4

[constraints]
assumptions = [
  { name = "env_no_push_and_pop_when_empty", expr = "!(push && pop && empty)", note = "Environment sanity assumption" }
]
covers = [
  { name = "cover_req_ack", expr = "req ##[1:4] ack", note = "Observe request/ack path" }
]

[kpi]
min_time_reduction_percent = 30.0
require_bug_or_coverage = true
""",
    )

    _write_if_missing(
        target / "rtl" / "fifo_buggy.sv",
        """module fifo_buggy #(
  parameter int DEPTH = 4,
  parameter int LEVEL_W = 3
) (
  input  logic             clk,
  input  logic             rst_n,
  input  logic             req,
  output logic             ack,
  input  logic             push,
  input  logic             pop,
  output logic             full,
  output logic             empty,
  output logic             valid
);

  logic [LEVEL_W-1:0] level;

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      level <= '0;
      ack <= 1'b0;
    end else begin
      ack <= req;

      if (push && !full && !(pop && !empty)) begin
        level <= level + 1'b1;
      end else if (pop && !empty && !(push && !full)) begin
        level <= level - 1'b1;
      end
    end
  end

  // Intentional bug: should be (level == DEPTH), not DEPTH-1.
  assign full = (level == (DEPTH - 1));
  assign empty = (level == '0);
  assign valid = !empty;

endmodule
""",
    )

    _write_if_missing(
        target / "spec" / "intent.md",
        """# Pilot Intent

- If req then ack next cycle.
- Never push and full.
- Never pop and empty.
- valid should be low right after reset.
""",
    )

    _write_if_missing(
        target / "ci" / "run-pilot.sh",
        """#!/usr/bin/env bash
set -euo pipefail

CFG=${1:-formalchip.toml}

formalchip doctor --config "$CFG"
formalchip synth --config "$CFG" --deterministic --summary-json .formalchip/preview/synth-summary.json
set +e
formalchip run --config "$CFG"
rc=$?
set -e
echo "formalchip_run_exit=${rc}"

LAST_RUN=$(ls -1 .formalchip/runs | tail -n 1)
RUN_DIR=".formalchip/runs/${LAST_RUN}"
formalchip report --run-dir "${RUN_DIR}" --format json --include-gate > "${RUN_DIR}/report/summary.ci.json"
formalchip kpi --run-dir "${RUN_DIR}" --config "$CFG" --format json > "${RUN_DIR}/report/kpi.ci.json"

echo "Pilot completed: ${RUN_DIR}"
""",
        executable=True,
    )

    _write_if_missing(
        target / "metrics" / "baseline-study-template.csv",
        """participant,block,baseline_minutes_to_first_meaningful_properties,formalchip_minutes_to_first_meaningful_properties,baseline_property_count,formalchip_property_count,notes
P1,fifo,,,,,
P2,fifo,,,,,
""",
    )

    _write_if_missing(
        target / "README.md",
        """# FormalChip Open-Source Pilot

This scaffold is designed for the "Open-source RTL assertion synthesis + evidence pack" experiment.

## What it includes

- `rtl/fifo_buggy.sv`: open FIFO-style block with an intentional correctness bug.
- `formalchip.toml`: SymbiYosys engine config + canonical 10 property templates.
- `formalchip.toml`: SymbiYosys engine config + canonical 10 property templates + constraints/KPI policy.
- `spec/intent.md`: minimal natural-language intent input.
- `ci/run-pilot.sh`: reproducible CI sequence (doctor -> synth -> run -> report -> kpi).
- `metrics/baseline-study-template.csv`: template for the time-to-first-properties study.

## Run (on a machine with tools installed)

Required tools in PATH:

- `sby`
- `yosys`
- an SMT solver (`z3`, `boolector`, or similar)

Commands:

```bash
formalchip doctor --config formalchip.toml
formalchip synth --config formalchip.toml --deterministic
./ci/run-pilot.sh
```

The run directory contains:

- generated properties by iteration
- formal logs and failures/counterexamples
- witness/trace artifacts (if produced by the backend)
- `report/summary.json`, `report/summary.md`, `report/gate_verdict.json`, `report/kpi.json`
- evidence tarball under `evidence/`
""",
    )


def _write_if_missing(path: Path, content: str, executable: bool = False) -> None:
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    if executable:
        mode = path.stat().st_mode
        path.chmod(mode | 0o111)

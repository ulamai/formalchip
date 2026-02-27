from __future__ import annotations

import argparse
from pathlib import Path

from .config import load_config
from .evidence import build_evidence_pack
from .loop import run_formalchip


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="formalchip", description="FormalChip verification acceleration loop")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_init = sub.add_parser("init", help="Create a starter FormalChip project")
    p_init.add_argument("path", nargs="?", default=".", help="Target directory")

    p_run = sub.add_parser("run", help="Run proposal->formal->repair loop")
    p_run.add_argument("--config", required=True, help="Path to formalchip config (toml/json/yaml)")
    p_run.add_argument("--max-iters", type=int, default=None, help="Override max iterations")

    p_ev = sub.add_parser("evidence", help="Build evidence pack for an existing run dir")
    p_ev.add_argument("--run-dir", required=True, help="Run directory (.formalchip/runs/<run-id>)")
    p_ev.add_argument("--config", required=False, help="Config path used for the run")
    p_ev.add_argument("--out", required=False, help="Output tar.gz path")

    args = parser.parse_args(argv)

    if args.cmd == "init":
        _init_project(Path(args.path).resolve())
        return 0

    if args.cmd == "run":
        cfg = load_config(args.config)
        state = run_formalchip(cfg, max_iterations_override=args.max_iters)
        print(f"run_id={state.run_id}")
        print(f"status={state.status}")
        print(f"iterations={len(state.iterations)}")
        if state.evidence_pack:
            print(f"evidence_pack={state.evidence_pack}")
        return 0 if state.status == "pass" else 1

    if args.cmd == "evidence":
        run_dir = Path(args.run_dir).resolve()
        if args.config:
            config_path = Path(args.config).resolve()
        else:
            state_path = run_dir / "state.json"
            if not state_path.exists():
                raise FileNotFoundError("--config is required when state.json is not present")
            import json

            state = json.loads(state_path.read_text(encoding="utf-8"))
            config_path = Path(state["config_path"])

        out = Path(args.out).resolve() if args.out else None
        pack = build_evidence_pack(run_dir=run_dir, config_path=config_path, tool_versions={}, output_path=out)
        print(pack)
        return 0

    return 2


def _init_project(target: Path) -> None:
    target.mkdir(parents=True, exist_ok=True)
    (target / "rtl").mkdir(parents=True, exist_ok=True)
    (target / "spec").mkdir(parents=True, exist_ok=True)

    _write_if_missing(
        target / "formalchip.toml",
        """[project]
name = "pilot-control"
rtl_files = ["rtl/top.sv"]
top_module = "top"
clock = "clk"
reset = "rst_n"
reset_active_low = true

[llm]
backend = "deterministic"
model = "formalchip-template-v1"

[engine]
# Use `symbiyosys` for real proofs if installed. `mock` is CI-safe.
kind = "mock"
pass_after = 2
# command = "sby"
# sby_file = "formal/top.sby"

[loop]
max_iterations = 3
workdir = ".formalchip/runs"

[[specs]]
kind = "text"
path = "spec/control_logic.md"

[[specs]]
kind = "register_csv"
path = "spec/registers.csv"

[[specs]]
kind = "rule_table_csv"
path = "spec/protocol_rules.csv"

[[libraries]]
kind = "handshake"
req = "req"
ack = "ack"
bound = 4

[[libraries]]
kind = "fifo_safety"
full = "fifo_full"
empty = "fifo_empty"
push = "fifo_push"
pop = "fifo_pop"

[[libraries]]
kind = "reset_sequence"
signal = "valid"
value = "1'b0"
latency = 1
""",
    )

    _write_if_missing(
        target / "rtl" / "top.sv",
        """module top(
  input  logic clk,
  input  logic rst_n,
  input  logic req,
  output logic ack,
  input  logic fifo_push,
  input  logic fifo_pop,
  output logic fifo_full,
  output logic fifo_empty,
  output logic valid
);

  logic [31:0] status_q;
  logic [31:0] ctrl_q;

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      status_q <= 32'h0;
      ctrl_q <= 32'h0;
      ack <= 1'b0;
      valid <= 1'b0;
    end else begin
      ack <= req;
      valid <= !fifo_empty;
    end
  end

  assign fifo_full = 1'b0;
  assign fifo_empty = 1'b1;
endmodule
""",
    )

    _write_if_missing(
        target / "spec" / "control_logic.md",
        """# Control Logic Intent

- If req then ack next cycle.
- Never fifo_push and fifo_full.
- valid should be low right after reset.
""",
    )

    _write_if_missing(
        target / "spec" / "registers.csv",
        """name,address,width,reset,access
STATUS,0x00,32,0x0,ro
CTRL,0x04,32,0x0,rw
""",
    )

    _write_if_missing(
        target / "spec" / "protocol_rules.csv",
        """rule_id,condition,guarantee
R1,req,ack
R2,fifo_full,!fifo_push
R3,fifo_empty,!fifo_pop
""",
    )

    print(f"Initialized FormalChip project at {target}")


def _write_if_missing(path: Path, content: str) -> None:
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


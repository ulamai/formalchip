from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from formalchip.config import load_config
from formalchip.loop import run_formalchip


class LoopTests(unittest.TestCase):
    def test_run_loop_with_mock_engine(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "rtl").mkdir()
            (root / "spec").mkdir()

            (root / "rtl" / "top.sv").write_text(
                """module top(input logic clk, input logic rst_n, input logic req, output logic ack);
always_ff @(posedge clk or negedge rst_n) begin
  if (!rst_n) ack <= 1'b0;
  else ack <= req;
end
endmodule
""",
                encoding="utf-8",
            )
            (root / "spec" / "control.md").write_text(
                "- If req then ack next cycle.\n",
                encoding="utf-8",
            )
            (root / "spec" / "regs.csv").write_text(
                "name,address,width,reset,access\nSTATUS,0x00,32,0x0,ro\n",
                encoding="utf-8",
            )

            (root / "formalchip.toml").write_text(
                """[project]
name = "unit"
rtl_files = ["rtl/top.sv"]
top_module = "top"
clock = "clk"
reset = "rst_n"
reset_active_low = true

[llm]
backend = "deterministic"

[engine]
kind = "mock"
pass_after = 2

[loop]
max_iterations = 3
workdir = ".formalchip/runs"

[[specs]]
kind = "text"
path = "spec/control.md"

[[specs]]
kind = "register_csv"
path = "spec/regs.csv"
""",
                encoding="utf-8",
            )

            cfg = load_config(root / "formalchip.toml")
            state = run_formalchip(cfg)

            self.assertEqual(state.status, "pass")
            self.assertEqual(len(state.iterations), 2)
            self.assertIsNotNone(state.evidence_pack)
            assert state.evidence_pack is not None
            self.assertTrue(Path(state.evidence_pack).exists())


if __name__ == "__main__":
    unittest.main()


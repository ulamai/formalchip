from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from formalchip.config import load_config
from formalchip.doctor import run_doctor


class DoctorTests(unittest.TestCase):
    def test_doctor_ok_for_valid_mock_project(self) -> None:
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
            (root / "spec" / "control.md").write_text("- If req then ack next cycle.\n", encoding="utf-8")
            (root / "formalchip.toml").write_text(
                """[project]
name = "doctor-ok"
rtl_files = ["rtl/top.sv"]
top_module = "top"
clock = "clk"
reset = "rst_n"
reset_active_low = true

[llm]
backend = "deterministic"

[engine]
kind = "mock"

[loop]
max_iterations = 2
workdir = ".formalchip/runs"

[[specs]]
kind = "text"
path = "spec/control.md"
""",
                encoding="utf-8",
            )

            cfg = load_config(root / "formalchip.toml")
            report = run_doctor(cfg)
            self.assertTrue(report.ok)
            self.assertGreater(report.candidate_count, 0)

    def test_doctor_reports_missing_rtl(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "spec").mkdir()
            (root / "spec" / "control.md").write_text("- If req then ack next cycle.\n", encoding="utf-8")
            (root / "formalchip.toml").write_text(
                """[project]
name = "doctor-missing"
rtl_files = ["rtl/missing.sv"]
top_module = "top"

[llm]
backend = "deterministic"

[engine]
kind = "mock"

[loop]
max_iterations = 2
workdir = ".formalchip/runs"

[[specs]]
kind = "text"
path = "spec/control.md"
""",
                encoding="utf-8",
            )

            cfg = load_config(root / "formalchip.toml")
            report = run_doctor(cfg)
            self.assertFalse(report.ok)
            self.assertTrue(any("Missing RTL files" in err for err in report.errors))


if __name__ == "__main__":
    unittest.main()


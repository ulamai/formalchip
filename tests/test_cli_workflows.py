from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from formalchip.cli import main


class CLIWorkflowTests(unittest.TestCase):
    def test_synth_and_doctor_commands(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            rc = main(["init", str(root)])
            self.assertEqual(rc, 0)

            cfg = root / "formalchip.toml"
            out = root / "generated.sv"
            summary = root / "generated.json"

            rc = main(["doctor", "--config", str(cfg)])
            self.assertEqual(rc, 0)

            rc = main([
                "synth",
                "--config",
                str(cfg),
                "--out",
                str(out),
                "--summary-json",
                str(summary),
                "--deterministic",
            ])
            self.assertEqual(rc, 0)
            self.assertTrue(out.exists())
            self.assertTrue(summary.exists())

    def test_pilot_init_command(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "open-pilot"
            rc = main(["pilot-init", str(root)])
            self.assertEqual(rc, 0)
            self.assertTrue((root / "formalchip.toml").exists())
            self.assertTrue((root / "rtl" / "fifo_buggy.sv").exists())
            self.assertTrue((root / "ci" / "run-pilot.sh").exists())


if __name__ == "__main__":
    unittest.main()

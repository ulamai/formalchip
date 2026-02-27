from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from formalchip.cli import main
from formalchip.config import load_config
from formalchip.kpi import compute_kpi_report
from formalchip.loop import run_formalchip
from formalchip.templates import export_engine_template, supported_engine_templates


class KPIAndTemplateTests(unittest.TestCase):
    def test_compute_kpi_report(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            rc = main(["init", str(root)])
            self.assertEqual(rc, 0)

            cfg = load_config(root / "formalchip.toml")
            state = run_formalchip(cfg)
            run_dir = cfg.loop.workdir / state.run_id

            report = compute_kpi_report(run_dir=run_dir, policy=cfg.kpi)
            self.assertEqual(report["run_id"], state.run_id)
            self.assertIn("overall_success", report)
            self.assertTrue((run_dir / "report" / "kpi.json").exists())

    def test_engine_template_export(self) -> None:
        engines = supported_engine_templates()
        self.assertIn("vcformal", engines)
        self.assertIn("jasper", engines)
        self.assertIn("questa", engines)

        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "vcformal.tcl"
            export_engine_template("vcformal", out)
            self.assertTrue(out.exists())
            text = out.read_text(encoding="utf-8")
            self.assertIn("FORMALCHIP_PROPERTY_FILE", text)


if __name__ == "__main__":
    unittest.main()


from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from formalchip.spec import parse_ipxact, parse_register_csv, parse_rule_table_csv, parse_text_spec


class SpecIngestTests(unittest.TestCase):
    def test_text_spec_parser(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "spec.md"
            p.write_text("# Title\n- If req then ack next cycle.\n", encoding="utf-8")
            clauses = parse_text_spec(p)
            self.assertEqual(len(clauses), 1)
            self.assertIn("req", clauses[0].text.lower())

    def test_register_csv_parser(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "regs.csv"
            p.write_text(
                "name,address,width,reset,access\nSTATUS,0x00,32,0x0,ro\n",
                encoding="utf-8",
            )
            clauses = parse_register_csv(p)
            self.assertGreaterEqual(len(clauses), 2)
            self.assertTrue(any("read-only" in c.text.lower() for c in clauses))

    def test_ipxact_parser(self) -> None:
        xml = """<?xml version=\"1.0\"?>
<spirit:component xmlns:spirit=\"http://www.spiritconsortium.org/XMLSchema/SPIRIT/1685-2009\">
  <spirit:memoryMaps>
    <spirit:memoryMap>
      <spirit:addressBlock>
        <spirit:register>
          <spirit:name>STATUS</spirit:name>
          <spirit:reset>
            <spirit:value>0x0</spirit:value>
          </spirit:reset>
        </spirit:register>
      </spirit:addressBlock>
    </spirit:memoryMap>
  </spirit:memoryMaps>
</spirit:component>
"""
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "csr.xml"
            p.write_text(xml, encoding="utf-8")
            clauses = parse_ipxact(p)
            self.assertEqual(len(clauses), 1)
            self.assertIn("status", clauses[0].text.lower())

    def test_rule_table_parser(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "rules.csv"
            p.write_text("rule_id,condition,guarantee\nR1,req,ack\n", encoding="utf-8")
            clauses = parse_rule_table_csv(p)
            self.assertEqual(len(clauses), 1)
            self.assertIn("then ack", clauses[0].text.lower())


if __name__ == "__main__":
    unittest.main()


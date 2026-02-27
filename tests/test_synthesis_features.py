from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from formalchip.config import LibraryPattern
from formalchip.models import SpecClause
from formalchip.spec.register_csv import parse_register_csv
from formalchip.synthesis import SynthesisInputs, is_placeholder_candidate, synthesize_candidates


class SynthesisFeatureTests(unittest.TestCase):
    def test_register_ro_mapping_generates_real_assertion(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "regs.csv"
            p.write_text(
                "name,address,width,reset,access\nSTATUS,0x00,32,0x0,ro\n",
                encoding="utf-8",
            )
            clauses = parse_register_csv(
                p,
                {
                    "signal_template": "{name_lower}_q",
                    "sw_we_signal": "sw_we",
                    "sw_addr_signal": "sw_addr",
                    "sw_addr_width": 32,
                },
            )

            inputs = SynthesisInputs(
                clock="clk",
                reset="rst_n",
                reset_active_low=True,
                known_signals={"clk", "rst_n", "status_q", "sw_we", "sw_addr"},
            )
            candidates = synthesize_candidates(clauses, [], inputs)

            ro_candidates = [c for c in candidates if c.name.endswith("_ro")]
            self.assertEqual(len(ro_candidates), 1)
            self.assertIn("sw_addr", ro_candidates[0].body)
            self.assertFalse(is_placeholder_candidate(ro_candidates[0]))

    def test_inline_library_property(self) -> None:
        inputs = SynthesisInputs(
            clock="clk",
            reset="rst_n",
            reset_active_low=True,
            known_signals={"clk", "rst_n", "a", "b"},
        )
        libs = [
            LibraryPattern(
                kind="inline",
                options={
                    "name": "a_implies_b",
                    "expr": "a |-> b",
                    "property_kind": "assume",
                },
            )
        ]

        candidates = synthesize_candidates([], libs, inputs)
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0].kind, "assume")
        self.assertIn("a |-> b", candidates[0].body)

    def test_text_reset_intent_pattern(self) -> None:
        clause = SpecClause(
            clause_id="t1",
            text="valid should be low right after reset.",
            source="spec.md",
            tags=["text"],
        )
        inputs = SynthesisInputs(
            clock="clk",
            reset="rst_n",
            reset_active_low=True,
            known_signals={"clk", "rst_n", "valid"},
        )
        candidates = synthesize_candidates([clause], [], inputs)
        self.assertEqual(len(candidates), 1)
        self.assertIn("valid == 1'b0", candidates[0].body)
        self.assertFalse(is_placeholder_candidate(candidates[0]))

    def test_canonical_10_library_count(self) -> None:
        inputs = SynthesisInputs(
            clock="clk",
            reset="rst_n",
            reset_active_low=True,
            known_signals={"clk", "rst_n", "req", "ack", "push", "pop", "full", "empty", "level", "valid"},
        )
        libs = [
            LibraryPattern(
                kind="canonical_10",
                options={
                    "req": "req",
                    "ack": "ack",
                    "push": "push",
                    "pop": "pop",
                    "full": "full",
                    "empty": "empty",
                    "level": "level",
                    "level_width": 3,
                    "level_max": "4",
                    "valid": "valid",
                    "bound": 4,
                },
            )
        ]

        candidates = synthesize_candidates([], libs, inputs)
        self.assertEqual(len(candidates), 10)

    def test_signal_aliases_reduce_placeholders(self) -> None:
        inputs = SynthesisInputs(
            clock="clk",
            reset="rst_n",
            reset_active_low=True,
            known_signals={"clk", "rst_n", "req", "ack"},
            signal_aliases={"request": "req", "acknowledge": "ack"},
        )
        libs = [
            LibraryPattern(
                kind="inline",
                options={
                    "name": "alias_req_ack",
                    "expr": "request |-> acknowledge",
                    "property_kind": "assert",
                },
            )
        ]
        candidates = synthesize_candidates([], libs, inputs)
        self.assertEqual(len(candidates), 1)
        self.assertIn("req |-> ack", candidates[0].body)
        self.assertFalse(is_placeholder_candidate(candidates[0]))


if __name__ == "__main__":
    unittest.main()

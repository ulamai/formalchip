# FormalChip

FormalChip is an UlamaI-style control loop for hardware formal verification:

1. Propose properties (SVA) from mixed specification artifacts.
2. Run a formal engine (SymbiYosys pilot, with wrappers for proprietary tools).
3. Parse counterexamples / failures.
4. Repair and retry.
5. Emit a reproducible signoff evidence pack.

## Why this exists

Hardware teams already use formal engines. The bottleneck is writing and maintaining properties, constraints, and audit artifacts. FormalChip focuses on reducing adoption cost and broadening coverage.

## Current MVP capabilities

- Spec ingestion:
  - Free-form text/markdown clauses
  - Register CSV definitions
  - IP-XACT register XML
  - Generic rule-table CSV
- Property synthesis:
  - Reset, handshake, and table-driven rule templates
  - Reusable library patterns configured in `formalchip.toml`
- Formal adapters:
  - `symbiyosys` (real command runner)
  - `mock` (for local testing/CI without a solver)
  - `vcformal`, `jasper`, `questa` command wrappers
- Evidence packs:
  - Run state, config, tool versions, logs, generated SVAs
  - SHA-256 manifest and tarball export

## Quickstart

```bash
python -m formalchip init examples/pilot
python -m formalchip run --config examples/pilot/formalchip.toml
```

Inspect artifacts in `.formalchip/runs/<run-id>/`.

## CLI

```bash
formalchip init [path]
formalchip run --config formalchip.toml [--max-iters N]
formalchip evidence --run-dir .formalchip/runs/<run-id> [--out evidence.tar.gz]
```

## Configuration

See [`examples/pilot/formalchip.toml`](examples/pilot/formalchip.toml).

Key sections:

- `[project]`: RTL files, top module, clock/reset
- `[llm]`: `backend = "deterministic" | "command"`
- `[engine]`: `kind = "symbiyosys" | "mock" | "vcformal" | "jasper" | "questa"`
- `[loop]`: iteration controls and run directory
- `[[specs]]`: spec artifacts
- `[[libraries]]`: reusable intent patterns

## Notes

- SymbiYosys must be installed to run the open-source formal path.
- Proprietary engines are represented as scriptable wrappers in this MVP.


# FormalChip

FormalChip is an UlamaI-style control loop for hardware formal verification:

1. Propose properties (SVA) from mixed specification artifacts.
2. Run a formal engine (SymbiYosys pilot, with wrappers for proprietary tools).
3. Parse counterexamples / failures.
4. Repair and retry.
5. Emit reproducible signoff evidence + run summaries.

## What is useful in v1

- Preflight checks with `formalchip doctor`:
  - missing RTL/spec files
  - engine command availability
  - top-module detection sanity checks
  - synthesis quality signal (placeholder property counts)
- Property preview with `formalchip synth` before formal runtime cost.
- Spec ingestion:
  - Free-form text clauses
  - Register CSV definitions with optional bus mapping
  - IP-XACT register XML
  - Generic rule-table CSV
- Property synthesis:
  - Reset, handshake, FIFO, and table-driven templates
  - Inline custom properties (`[[libraries]] kind = "inline"`)
- Formal adapters:
  - `symbiyosys` (real command runner)
  - `mock` (CI-safe testing)
  - `vcformal`, `jasper`, `questa` command wrappers
- Run artifacts:
  - state + trace logs
  - generated property files per iteration
  - run summary (`report/summary.json`, `report/summary.md`)
  - evidence pack with manifest + hashes

## Quickstart

```bash
python3 -m formalchip init examples/pilot
python3 -m formalchip doctor --config examples/pilot/formalchip.toml
python3 -m formalchip synth --config examples/pilot/formalchip.toml --deterministic
python3 -m formalchip run --config examples/pilot/formalchip.toml
```

Inspect artifacts in `examples/pilot/.formalchip/runs/<run-id>/`.

## CLI

```bash
formalchip init [path]
formalchip doctor --config formalchip.toml
formalchip synth --config formalchip.toml [--out properties.sv] [--summary-json synth.json] [--deterministic]
formalchip run --config formalchip.toml [--max-iters N] [--skip-doctor]
formalchip report --run-dir .formalchip/runs/<run-id> [--format text|json]
formalchip evidence --run-dir .formalchip/runs/<run-id> [--out evidence.tar.gz]
```

## Config patterns

See [`examples/pilot/formalchip.toml`](examples/pilot/formalchip.toml).

Key sections:

- `[project]`: RTL files, top module, clock/reset
- `[llm]`: `backend = "deterministic" | "command"`
- `[engine]`: `kind = "symbiyosys" | "mock" | "vcformal" | "jasper" | "questa"`
- `[loop]`: iteration controls and run directory
- `[[specs]]`: spec artifacts
- `[[libraries]]`: reusable intent patterns + inline custom properties

### Register CSV mapping options

For `[[specs]] kind = "register_csv"`, optional fields:

- `signal_template` (default: `"{name_lower}_q"`)
- `sw_we_signal`
- `sw_addr_signal`
- `sw_addr_width` (default: `32`)

When these are set and signals exist in RTL, FormalChip emits real read-only CSR assertions instead of placeholders.

### Inline property library

```toml
[[libraries]]
kind = "inline"
name = "ctrl_write_decode_valid"
expr = "(sw_we && (sw_addr == 32'h00000004)) |-> !fifo_full"
property_kind = "assert" # assert | assume | cover
```

## SymbiYosys notes

- SymbiYosys must be installed to run the open-source formal path.
- Use `[engine] kind = "symbiyosys"` and optionally `command` / `sby_file` in config.


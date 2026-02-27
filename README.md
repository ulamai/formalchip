# FormalChip

FormalChip is a UlamAI-style control loop for hardware formal verification:

1. Propose properties (SVA) from mixed specification artifacts.
2. Run a formal engine (SymbiYosys pilot, with wrappers for proprietary tools).
3. Parse counterexamples / failures.
4. Repair and retry.
5. Emit reproducible signoff evidence + gate/KPI reports.

## Productized v0.1.x capabilities

- Preflight checks with `formalchip doctor`:
  - missing RTL/spec files
  - engine command availability
  - top-module detection sanity checks
  - synthesis quality signal (placeholder ratio)
- Property preview with `formalchip synth`.
- Open-source pilot scaffold with `formalchip pilot-init`.
- Spec ingestion:
  - free-form text clauses
  - register CSV definitions with optional bus mapping
  - IP-XACT register XML
  - rule-table CSV
- Property synthesis:
  - reset, handshake, FIFO, table-driven templates
  - inline custom properties (`[[libraries]] kind = "inline"`)
  - canonical 10-pattern pilot library (`[[libraries]] kind = "canonical_10"`)
  - signal alias resolution to reduce placeholder generation
  - structured constraints mapped into assumptions/covers
- Formal adapters:
  - `symbiyosys` (real command runner)
  - `mock` (CI-safe testing)
  - `vcformal`, `jasper`, `questa` command wrappers
  - proprietary engine template export via `formalchip engine-template`
- Run artifacts:
  - state + trace logs
  - generated property files per iteration
  - run summary (`report/summary.json`, `report/summary.md`)
  - machine-readable gate verdict (`report/gate_verdict.json`)
  - KPI report (`report/kpi.json`)
  - evidence pack with manifest + hashes + gate snapshot

## Quickstart

```bash
python3 -m formalchip init examples/pilot
python3 -m formalchip doctor --config examples/pilot/formalchip.toml
python3 -m formalchip synth --config examples/pilot/formalchip.toml --deterministic
python3 -m formalchip run --config examples/pilot/formalchip.toml
python3 -m formalchip report --run-dir examples/pilot/.formalchip/runs/<run-id> --include-gate
python3 -m formalchip kpi --run-dir examples/pilot/.formalchip/runs/<run-id> --config examples/pilot/formalchip.toml
```

## CLI

```bash
formalchip init [path]
formalchip pilot-init [path]
formalchip doctor --config formalchip.toml
formalchip synth --config formalchip.toml [--out properties.sv] [--summary-json synth.json] [--deterministic]
formalchip run --config formalchip.toml [--max-iters N] [--skip-doctor]
formalchip report --run-dir .formalchip/runs/<run-id> [--format text|json] [--include-gate]
formalchip kpi --run-dir .formalchip/runs/<run-id> [--config formalchip.toml] [--baseline-csv study.csv]
formalchip evidence --run-dir .formalchip/runs/<run-id> [--out evidence.tar.gz]
formalchip engine-template --engine vcformal|jasper|questa [--out run.tcl]
```

## Configuration highlights

See [`examples/pilot/formalchip.toml`](examples/pilot/formalchip.toml).

Key sections:

- `[project]`: RTL files, top module, clock/reset, signal aliases
- `[llm]`: `backend = "deterministic" | "command"`
- `[engine]`: `kind = "symbiyosys" | "mock" | "vcformal" | "jasper" | "questa"`
- `[loop]`: iteration controls and run directory
- `[constraints]`: structured assumptions and covers
- `[kpi]`: pilot success policy
- `[[specs]]`: spec artifacts
- `[[libraries]]`: reusable intent patterns and custom assertions

### Constraints / assumptions UX

```toml
[constraints]
assumptions = [
  { name = "env_req_not_glitchy", expr = "req |=> req || !req", note = "example" }
]
covers = [
  { name = "cover_req_ack", expr = "req ##[1:4] ack" }
]
```

### Signal alias mapping

```toml
[project]
signal_aliases = { request = "req", acknowledge = "ack" }
```

This helps map natural-language/spec tokens to RTL signal names.

## Reproducible runtime

- `Dockerfile` uses a pinned Debian snapshot (`formal-tools.lock`) and installs formal toolchain packages.
- `.devcontainer/devcontainer.json` provides a consistent local dev environment.
- `scripts/print-tool-versions.sh` records resolved tool versions.

## Real formal CI

- `.github/workflows/formal-pilot.yml` builds runtime image, runs the open-source pilot with SymbiYosys, generates evidence/report/KPI artifacts, and applies a gate check.
- `.github/workflows/tests.yml` runs unit tests on pushes/PRs.

## Proprietary engine templates

Export starter scripts:

```bash
formalchip engine-template --engine vcformal --out vcformal.run.tcl
formalchip engine-template --engine jasper --out jasper.run.tcl
formalchip engine-template --engine questa --out questa.run.tcl
```

## Product ops docs

- [On-Prem Deployment](docs/ops/onprem-deployment.md)
- [Data Policy Template](docs/ops/data-policy.md)
- [Support Model](docs/ops/support-model.md)

## Notes

- SymbiYosys path requires `sby`, `yosys`, and solver binaries in PATH.
- Proprietary templates are starting points and require adaptation to each EDA environment.


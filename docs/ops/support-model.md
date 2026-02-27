# Support Model

## Severity levels

- Sev1: Blocking production/signoff flow.
- Sev2: Major workflow degradation with workaround.
- Sev3: Minor bug or quality issue.

## Response targets (example)

- Sev1: first response <= 2 business hours.
- Sev2: first response <= 1 business day.
- Sev3: first response <= 3 business days.

## Runbook ownership

- Verification engineering owns property/constraint intent.
- CAD/DevOps owns runtime/toolchain stability.
- Security/compliance owns retention and access controls.

## Escalation data package

Include:

- `state.json`
- `trace.jsonl`
- `report/summary.json`
- `report/gate_verdict.json`
- evidence tarball from `evidence/`

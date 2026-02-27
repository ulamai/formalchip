# Data Handling and Privacy Policy (Template)

This template is intended for FormalChip on-prem and customer-managed deployments.

## Principles

- Customer RTL/spec data remains customer-owned.
- No training on customer data by default.
- No external transmission unless explicitly configured.

## Operational controls

- Disable network egress for formal workers where required.
- Keep run directories under customer-controlled storage.
- Apply retention policy for logs, traces, and evidence packs.
- Encrypt backups/artifacts at rest.

## LLM backend policy

- `deterministic` backend keeps all data local.
- `command` backend must point to approved endpoints/tools.
- Operators must document backend data-flow and retention behavior.

## Retention recommendations

- Active debug artifacts: 30-90 days.
- Signoff evidence packs: align to compliance/safety requirements.
- Sensitive trace files: redact or purge per policy.

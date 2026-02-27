# On-Prem Deployment Guide

FormalChip is designed for IP-sensitive hardware teams and supports on-prem/air-gapped deployment.

## Deployment modes

- Single-node container (`Dockerfile`) for pilot teams.
- Multi-runner CI deployment with isolated workers for formal jobs.
- Air-gapped mirror with preloaded Python/artifact dependencies.

## Recommended architecture

1. Git service (internal mirror) for RTL/spec repositories.
2. Formal runners with local license/tool access.
3. Artifact store for run evidence packs.
4. Optional internal API gateway for command-based LLM backends.

## Runtime hardening

- Run as non-root user.
- Use read-only mounts for input RTL/spec paths when possible.
- Write run artifacts to dedicated workspace volumes.
- Restrict egress for air-gapped contexts.

## Upgrade policy

- Pin runtime via `formal-tools.lock` and Docker snapshot args.
- Promote versions through `dev -> staging -> production` with golden pilot regressions.
- Archive evidence packs for each promoted release.

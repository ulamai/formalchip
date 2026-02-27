#!/usr/bin/env bash
set -euo pipefail

echo "formalchip_version=$(python3 - <<'PY'
import tomllib, pathlib
p = pathlib.Path('pyproject.toml')
print(tomllib.loads(p.read_text())['project']['version'])
PY
)"

for t in sby yosys z3 boolector; do
  if command -v "$t" >/dev/null 2>&1; then
    case "$t" in
      sby) v=$($t --version 2>&1 | head -n 1) ;;
      yosys) v=$($t -V 2>&1 | head -n 1) ;;
      z3) v=$($t --version 2>&1 | head -n 1) ;;
      boolector) v=$($t --version 2>&1 | head -n 1) ;;
      *) v=$($t --version 2>&1 | head -n 1) ;;
    esac
    echo "${t}=${v}"
  else
    echo "${t}=not-installed"
  fi
done

#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

mkdir -p runtime exports database
rm -f runtime/guard.stop

: "${BOI_ACCOUNTS:=100000}"
: "${BOI_TRANSACTIONS:=1000000}"
: "${BOI_SPEED:=100x}"
: "${BOI_SEED:=20260101}"

export BOI_ACCOUNTS BOI_TRANSACTIONS BOI_SPEED BOI_SEED
export BOI_STOP_FILE="$ROOT/runtime/guard.stop"

python3 "$ROOT/backend/ecosystem.py"

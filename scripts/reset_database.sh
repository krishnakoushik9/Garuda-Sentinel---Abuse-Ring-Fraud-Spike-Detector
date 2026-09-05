#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
rm -f "$ROOT/database/ecosystem.db" "$ROOT/database/ecosystem.db-shm" \
  "$ROOT/database/ecosystem.db-wal" "$ROOT/database/simulation.stop" \
  "$ROOT/runtime/guard.stop"
sqlite3 "$ROOT/database/ecosystem.db" < "$ROOT/database/schema.sql"
echo "Reset database/ecosystem.db"

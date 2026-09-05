#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_DIR="$ROOT/build"

mkdir -p "$BUILD_DIR" "$ROOT/database"

if ! command -v cobc >/dev/null 2>&1; then
  echo "cobc was not found. On Ubuntu, run: scripts/install_ubuntu.sh" >&2
  exit 1
fi

gcc -O2 -Wall -Wextra -c "$ROOT/cobol/sqlite_bridge.c" -o "$BUILD_DIR/sqlite_bridge.o"
cobc -x -free -O2 \
  "$ROOT/cobol/banking_engine.cob" \
  "$BUILD_DIR/sqlite_bridge.o" \
  -lsqlite3 \
  -o "$BUILD_DIR/boi_banking_engine"

echo "Built $BUILD_DIR/boi_banking_engine"

# Build Core Banking Sentinel Agent (CBSA)
cobc -x -free -O2 "$ROOT/src/cobol/SENTINEL.cbl" -o "$BUILD_DIR/sentinel_agent"
echo "Built $BUILD_DIR/sentinel_agent (COBOL Sentinel Runtime Agent)"

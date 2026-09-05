#!/usr/bin/env bash
set -euo pipefail

sudo apt-get update
sudo apt-get install -y gnucobol gcc make sqlite3 libsqlite3-dev python3

echo "Installed GnuCOBOL, SQLite, and Python runtime dependencies."

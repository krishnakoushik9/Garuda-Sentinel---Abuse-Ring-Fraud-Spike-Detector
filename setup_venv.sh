#!/usr/bin/env bash
# setup_venv.sh - Creates the virtual environment and installs CPU-only dependencies without build isolation

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

echo -e "\033[1;36m=================================================="
echo -e "      SETTING UP PYTHON VIRTUAL ENVIRONMENT"
echo -e "==================================================\033[0m"

# 1. Clean up any existing partial environment and purge pip cache
if [ -d ".venv" ]; then
    echo "Removing existing .venv directory..."
    rm -rf .venv
fi

echo "Purging local pip cache to remove heavy CUDA files..."
pip cache purge || true

# 2. Create the virtual environment
echo "Creating new virtual environment in .venv..."
python3 -m venv .venv

# 3. Activate the virtual environment
echo "Activating virtual environment..."
source .venv/bin/activate

# 4. Upgrade pip and setuptools
echo "Upgrading pip, setuptools, and wheel..."
pip install --upgrade pip setuptools wheel

# 5. Pre-install numpy, torch, and build backends (tomlkit, poetry-core)
echo "Pre-installing numpy, torch, and package build backends..."
pip install numpy==1.26.4 torch==2.2.0 tomlkit poetry-core --extra-index-url https://download.pytorch.org/whl/cpu

# 6. Install all other requirements with CPU wheels priority and disabled build isolation
echo "Installing remaining project dependencies from requirements.txt..."
pip install -r requirements.txt --extra-index-url https://download.pytorch.org/whl/cpu --no-build-isolation

echo -e "\033[1;32m"
echo "=================================================="
echo "✓ Virtual environment successfully set up!"
echo "=================================================="
echo -e "\033[0m"
echo "You can now start the project using your launcher:"
echo "  java -jar run_launcher.jar"
echo "Or start the background servers directly:"
echo "  ./run_demo.sh"

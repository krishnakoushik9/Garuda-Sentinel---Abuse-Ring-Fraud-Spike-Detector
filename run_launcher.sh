#!/usr/bin/env bash
# ========================================================================
# BOI Garuda Sentinel Master Launcher & Native Executable Builder
# ========================================================================
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

JAR_PATH="$ROOT/launcher/target/garuda-sentinel-launcher-1.0.0.jar"
EXECUTABLE_PATH="$ROOT/garuda-launcher"

echo -e "\033[1;32m========================================================================\033[0m"
echo -e "\033[1;36m               BOI GARUDA SENTINEL LAUNCHER ORCHESTRATOR\033[0m"
echo -e "\033[1;32m========================================================================\033[0m"

# Ensure runtime directory exists
mkdir -p "$ROOT/runtime" "$ROOT/database" "$ROOT/exports"

# Verify Java Runtime Environment
if ! command -v java >/dev/null 2>&1; then
    echo -e "\033[1;31mError: Java Runtime (java) is not installed!\033[0m"
    echo "Please install OpenJDK 21 or later to proceed."
    exit 1
fi

JAVA_VERSION_STR=$(java -version 2>&1 | head -n 1)
echo -e "\033[1;34mDetected Java Runtime: $JAVA_VERSION_STR\033[0m"

# Always compile launcher to ensure updates are built
echo -e "\033[1;33mInitiating Maven build for launcher...\033[0m"
if ! command -v mvn >/dev/null 2>&1; then
    echo -e "\033[1;31mError: Maven (mvn) is not installed! Cannot compile the launcher.\033[0m"
    echo "Please install Maven or build the project in launcher/ directory manually."
    exit 1
fi
cd "$ROOT/launcher"
mvn clean package
cd "$ROOT"
echo -e "\033[1;32m✓ Shaded JAR compiled successfully!\033[0m"

# Generate the self-executing Linux binaries from the Shaded JAR
echo -e "\033[1;34mGenerating self-executing Linux Java binaries at: run_launcher and garuda-launcher ...\033[0m"

# Build run_launcher binary stub
cat << 'EOF' > "$ROOT/run_launcher"
#!/bin/sh
# BOI Garuda Sentinel Self-Executing Launcher Binary
# This binary runs directly using the local java runtime environment.
exec java -jar "$0" "$@"
EOF
cat "$JAR_PATH" >> "$ROOT/run_launcher"
chmod +x "$ROOT/run_launcher"

# Copy to run_launcher.jar
cp "$JAR_PATH" "$ROOT/run_launcher.jar"

# Copy to garuda-launcher
cp "$ROOT/run_launcher" "$EXECUTABLE_PATH"
chmod +x "$EXECUTABLE_PATH"

echo -e "\033[1;32m✓ Native self-executing Linux binaries and run_launcher.jar updated successfully!\033[0m"

# Display Server Warning
if [ -z "${DISPLAY:-}" ] && [ -z "${WAYLAND_DISPLAY:-}" ]; then
    echo -e "\033[1;33mWarning: No graphical display environment (X11/Wayland) detected!\033[0m"
    echo "The Java Swing GUI may fail to initialize if started in headless mode."
    echo "If running over SSH, please ensure X11 forwarding is enabled (ssh -X / ssh -Y)."
fi

echo -e "\033[1;34mStarting Garuda Sentinel GUI (PID and log details below)...\033[0m"
"$EXECUTABLE_PATH" > "$ROOT/runtime/launcher.log" 2>&1 &
LAUNCHER_PID=$!

echo -e "\033[1;32m✓ BOI Garuda Sentinel is active! (PID: $LAUNCHER_PID)\033[0m"
echo -e "Executable Binary: ./garuda-launcher"
echo -e "Runtime logs redirecting to: runtime/launcher.log"
echo -e "\033[1;35mEnjoy your self-executing terminal-free intelligence control panel!\033[0m"
echo -e "\033[1;32m========================================================================\033[0m"

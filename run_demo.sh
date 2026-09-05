#!/bin/bash
# run_demo.sh - PS2 Fraud Intelligence Platform Orchestration

echo -e "\033[1;32m=================================================="
echo -e "      PS2 FRAUD INTELLIGENCE DEMO LAUNCHER"
echo -e "==================================================\033[0m"

# Ensure clean termination of background servers on exit
cleanup() {
    echo -e "\n\033[1;31mStopping all background servers...\033[0m"
    kill $BACKEND_PID $MARKETING_PID $DASHBOARD_PID 2>/dev/null
    exit 0
}
trap cleanup SIGINT SIGTERM EXIT

# Verify database exists
DB_PATH="./database/ecosystem.db"
if [ ! -f "$DB_PATH" ]; then
    echo -e "\033[1;31mError: Database $DB_PATH not found!\033[0m"
    echo "Please ensure the COBOL simulator has run and SQLite database is populated."
    exit 1
fi
echo -e "\033[1;32m✓ Found ecosystem database ($DB_PATH)\033[0m"

# Start Backend API
echo "Starting Backend API on port 8000..."
PYTHONPATH=. .venv/bin/uvicorn src.api.main:app --host 0.0.0.0 --port 8000 > backend.log 2>&1 &
BACKEND_PID=$!
sleep 2

# Check if Backend API started successfully
if kill -0 $BACKEND_PID 2>/dev/null; then
    echo -e "\033[1;32m✓ Backend API running (PID: $BACKEND_PID)\033[0m"
else
    echo -e "\033[1;31mError: Backend API failed to start! Check backend.log\033[0m"
    cat backend.log
    exit 1
fi

# Start Marketing Site Server
echo "Starting Marketing Site Server on port 3001..."
.venv/bin/python -m http.server 3001 --directory frontend/marketing > marketing.log 2>&1 &
MARKETING_PID=$!

# Start Dashboard Server
echo "Starting Dashboard Server on port 3002..."
.venv/bin/python -m http.server 3002 --directory frontend/dashboard > dashboard.log 2>&1 &
DASHBOARD_PID=$!

sleep 2

# Output links
echo -e "\033[1;34m=================================================="
echo -e "PS2 Fraud Intelligence Platform is fully operational!"
echo -e "--------------------------------------------------"
echo -e "-> API Docs:       http://localhost:8000/docs"
echo -e "-> Marketing Site: http://localhost:3001"
echo -e "-> Dashboard App:  http://localhost:3002"
echo -e "=================================================="
echo -e "\033[0mPress [Ctrl+C] to stop all servers."

# Wait for children
wait

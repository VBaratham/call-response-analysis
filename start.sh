#!/bin/bash
# Start the Call/Response Analysis app

cd "$(dirname "$0")"

# Check if we're in a virtual environment
if [ -z "$VIRTUAL_ENV" ]; then
    echo "Warning: No virtual environment detected"
    echo "Consider running: source venv/bin/activate"
    echo ""
fi

# Start backend
echo "Starting backend server..."
cd backend
python -m uvicorn main:app --reload --port 8000

#!/bin/bash

# Plex Wrapped Startup Script

echo "🎬 Starting Plex Wrapped..."

# Check if config.yaml exists
if [ ! -f "config.yaml" ]; then
    echo "⚠️  config.yaml not found. Copying from example..."
    cp config.yaml.example config.yaml
    echo "📝 Please edit config.yaml with your API keys and URLs"
    exit 1
fi

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed"
    exit 1
fi

# Check Node
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is required but not installed"
    exit 1
fi

# Install Python dependencies if needed
if [ ! -d ".venv" ]; then
    echo "📦 Creating virtual environment..."
    uv venv

    echo "📦 Installing Python dependencies..."
    source .venv/bin/activate
    uv pip install -r requirements.txt > /dev/null 2>&1
fi

# Install frontend dependencies if needed
if [ ! -d "frontend/node_modules" ]; then
    echo "📦 Installing frontend dependencies..."
    cd frontend
    npm install > /dev/null 2>&1
    cd ..
fi

echo "🚀 Starting backend server..."
source .venv/bin/activate
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8766 &
BACKEND_PID=$!

echo "⏳ Waiting for backend to start..."
sleep 3

echo "🚀 Starting frontend server..."
cd frontend
HOST=0.0.0.0 PORT=8765 npm start &
FRONTEND_PID=$!
cd ..

echo ""
echo "✅ Plex Wrapped is running!"
echo "   Backend: http://localhost:8766 (accessible from network)"
echo "   Frontend: http://localhost:8765 (accessible from network)"
echo ""
echo "   Access from other devices on your network using your local IP"
echo ""
echo "Press Ctrl+C to stop both servers"

# Wait for user interrupt
trap "kill $BACKEND_PID $FRONTEND_PID; exit" INT
wait


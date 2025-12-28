#!/bin/bash
set -e

# Ensure data directory exists
mkdir -p /app/data

# Ensure tokens.json exists as a file (not a directory)
# Docker creates a directory when mounting a file that doesn't exist on the host
if [ -d "/app/data/tokens.json" ]; then
    echo "⚠️  tokens.json is a directory (Docker volume mount issue). Fixing..."
    rm -rf /app/data/tokens.json
fi

# Ensure tokens.json exists as an empty file if it doesn't exist
if [ ! -f "/app/data/tokens.json" ]; then
    echo "{}" > /app/data/tokens.json
    echo "✅ Created tokens.json"
fi

# Execute the main command
exec "$@"


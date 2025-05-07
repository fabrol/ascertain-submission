#!/bin/bash
set -e

# Install netcat if not already installed (for wait-for-it.sh)
apt-get update && apt-get install -y netcat-openbsd

# Make wait-for-it.sh executable
chmod +x wait-for-it.sh

# Wait for database to be ready
./wait-for-it.sh postgres:5432 60 

# Start the application
if [ "$ENVIRONMENT" = "development" ]; then
  echo "Starting server in development mode with hot-reloading..."
  exec uvicorn src.main:app --host 0.0.0.0 --port ${PORT:-8000} --reload --reload-dir src
else
  echo "Starting server in production mode..."
  exec uvicorn src.main:app --host 0.0.0.0 --port ${PORT:-8000}
fi 
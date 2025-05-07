#!/bin/bash
# Use: ./wait-for-it.sh host:port timeout [command]
# Example: ./wait-for-it.sh postgres:5432 30 -- echo "PostgreSQL is up!"

set -e

host=$(echo $1 | cut -d : -f 1)
port=$(echo $1 | cut -d : -f 2)
timeout=$2
shift 2

cmd=("$@")

until nc -z $host $port; do
  >&2 echo "Waiting for $host:$port..."
  sleep 1
  
  timeout=$((timeout - 1))
  if [ $timeout -le 0 ]; then
    >&2 echo "Timeout reached waiting for $host:$port - exiting"
    exit 1
  fi
done

>&2 echo "$host:$port is available"

# Execute the given command if present
if [ ${#cmd[@]} -gt 0 ]; then
  exec "${cmd[@]}"
fi 
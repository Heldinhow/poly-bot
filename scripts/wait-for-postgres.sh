#!/bin/bash
set -e

echo "Waiting for PostgreSQL to be ready..."

host="${DB_HOST:-postgres}"
port="${DB_PORT:-5432}"
user="${DB_USER:-polymarket}"
db="${DB_NAME:-polymarket}"

for i in $(seq 1 30); do
    if pg_isready -h "$host" -p "$port" -U "$user" > /dev/null 2>&1; then
        echo "PostgreSQL is ready!"
        break
    fi
    echo "PostgreSQL not ready yet, retrying in 2s... ($i/30)"
    sleep 2
done

# Verify connection
if ! pg_isready -h "$host" -p "$port" -U "$user" > /dev/null 2>&1; then
    echo "ERROR: PostgreSQL is not ready after 60s"
    exit 1
fi

echo "Starting application..."
exec "$@"

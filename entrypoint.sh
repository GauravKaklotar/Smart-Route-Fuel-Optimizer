#!/bin/bash
# ============================================================================
# Spotter AI — Docker Entrypoint
# Waits for PostgreSQL, runs migrations, collects static files, starts server.
# ============================================================================

set -e

echo "🔄 Waiting for PostgreSQL to be ready..."

while ! python -c "
import socket
import os
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
result = sock.connect_ex((os.getenv('POSTGRES_HOST', 'db'), int(os.getenv('POSTGRES_PORT', '5432'))))
sock.close()
exit(result)
" 2>/dev/null; do
    echo "⏳ PostgreSQL is not ready yet — retrying in 2s..."
    sleep 2
done

echo "✅ PostgreSQL is ready!"

echo "🔄 Running database migrations..."
python manage.py migrate --noinput

echo "🔄 Collecting static files..."
python manage.py collectstatic --noinput 2>/dev/null || true

echo "🚀 Starting Gunicorn server..."
exec gunicorn config.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 3 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -

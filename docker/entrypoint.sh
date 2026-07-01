#!/bin/bash
set -e

echo "Starting Forex Trading Bot..."

# Wait for database
echo "Waiting for PostgreSQL..."
while ! python -c "import psycopg2; psycopg2.connect(os.environ.get('DATABASE_URL', 'postgresql://forex_user:forex_password@localhost:5432/forex_trading'))" 2>/dev/null; do
  sleep 1
done
echo "PostgreSQL is ready!"

# Wait for Redis
echo "Waiting for Redis..."
while ! redis-cli -u $REDIS_URL ping > /dev/null 2>&1; do
  sleep 1
done
echo "Redis is ready!"

# Run migrations (if using Alembic)
# echo "Running database migrations..."
# alembic upgrade head

echo "All services ready. Starting application..."
exec "$@"

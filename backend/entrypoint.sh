#!/bin/sh
set -e

alembic upgrade head

if [ "${SEED_ON_START:-false}" = "true" ]; then
  python -m app.seed
fi

exec "$@"

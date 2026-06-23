#!/bin/sh
set -e

echo "Esperando a PostgreSQL..."
python -c "
import time, sys
from sqlalchemy import create_engine
from app.config import settings
for i in range(30):
    try:
        create_engine(settings.database_url).connect()
        sys.exit(0)
    except Exception as e:
        print('DB no lista aún:', e)
        time.sleep(2)
sys.exit(1)
"

echo "Aplicando migraciones (alembic upgrade head)..."
alembic upgrade head

echo "Iniciando servidor..."
exec gunicorn app.main:app \
    --workers ${WEB_CONCURRENCY:-2} \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000 \
    --access-logfile - \
    --error-logfile -

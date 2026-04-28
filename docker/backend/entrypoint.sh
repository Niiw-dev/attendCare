#!/bin/sh

echo "Esperando a PostgreSQL real..."

until python -c "
import psycopg2
import os
try:
    psycopg2.connect(
        dbname=os.environ.get('DB_NAME'),
        user=os.environ.get('DB_USER'),
        password=os.environ.get('DB_PASSWORD'),
        host='db',
        port=5432
    )
    print('DB OK')
except Exception:
    exit(1)
"; do
  sleep 2
done

echo "Base de datos lista 🚀"

python app/manage.py migrate
python app/manage.py runserver 0.0.0.0:8000
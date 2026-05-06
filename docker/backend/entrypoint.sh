#!/bin/sh

echo "Esperando a PostgreSQL..."

# Espera a que el puerto esté abierto
until nc -z db 5432; do
  echo "Postgres no está listo..."
  sleep 2
done

echo "PostgreSQL accesible"

# Espera conexión real
until python -c "
import psycopg2, os
psycopg2.connect(
    dbname=os.environ.get('DB_NAME'),
    user=os.environ.get('DB_USER'),
    password=os.environ.get('DB_PASSWORD'),
    host='db',
    port=5432
)
"; do
  echo "Esperando conexión real..."
  sleep 2
done

echo "Base de datos lista 🚀"

python manage.py migrate
python manage.py collectstatic --noinput

gunicorn core.wsgi:application --bind 0.0.0.0:8000
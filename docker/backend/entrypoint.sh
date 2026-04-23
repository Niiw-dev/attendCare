#!/bin/sh

echo "Esperando a la base de datos..."

while ! nc -z db 5432; do
  sleep 1
done

echo "Base de datos lista 🚀"

cd app

python manage.py migrate
python manage.py runserver 0.0.0.0:8000
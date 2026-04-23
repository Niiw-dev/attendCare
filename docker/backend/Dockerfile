FROM python:3.11

WORKDIR /app

RUN apt-get update && apt-get install -y netcat-openbsd

COPY requirements.txt .
COPY requirements-dev.txt .

RUN pip install --upgrade pip
RUN pip install -r requirements-dev.txt

COPY . /app

RUN chmod +x /app/docker/backend/entrypoint.sh

CMD ["sh", "/app/docker/backend/entrypoint.sh"]
FROM python:3.11-slim

WORKDIR /app

# Dépendances système nécessaires pour pyudev (détection USB)
RUN apt-get update && apt-get install -y \
    udev \
    libsystemd-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

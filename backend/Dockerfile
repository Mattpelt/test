FROM python:3.11-slim

WORKDIR /app

# Dépendances système : pyudev (USB) + libgphoto2 (MTP/PTP) + ffmpeg (vignettes)
RUN apt-get update && apt-get install -y \
    udev \
    libsystemd-dev \
    libgphoto2-dev \
    gphoto2 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

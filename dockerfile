# syntax=docker/dockerfile:1
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# System deps (keep minimal; add build-essential only if you have wheels failing)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
 && rm -rf /var/lib/apt/lists/*

# Install deps first (better layer caching)
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Install your package (src/ layout)
COPY pyproject.toml ./
COPY src ./src
RUN pip install --no-cache-dir .

# Install openpyxl for Excel export
RUN pip install --no-cache-dir openpyxl

# Copy export script
COPY export_trades.py ./

# Make a persistent data dir for sqlite
RUN mkdir -p /data

# Default paths
ENV DB_PATH=/data/trades.db
ENV EXPORT_PATH=/data/trades.xlsx

# Run the app
CMD ["python", "-m", "app.main"]

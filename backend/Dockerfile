# Use a minimal Python image
FROM python:3.12-slim

# Install system dependencies (specifically tesseract for OCR)
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    libtesseract-dev \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory in the container
WORKDIR /app

# Copy requirements file first to leverage Docker layer caching
COPY requirements.txt .

# Install Python dependencies (gunicorn already in requirements.txt)
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the backend files
COPY . .

# Expose port 10000 — Render's default port for Docker services
EXPOSE 10000

# Use a shell-form CMD so $PORT is expanded from Render's runtime environment.
# Render injects PORT=10000 automatically. Fallback to 10000 if not set.
CMD gunicorn --bind 0.0.0.0:${PORT:-10000} --timeout 600 --workers 1 main:app

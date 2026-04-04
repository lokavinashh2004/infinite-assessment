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

# Install Python dependencies, and add gunicorn for production serving
RUN pip install --no-cache-dir -r requirements.txt gunicorn

# Copy the rest of the backend files
COPY . .

# Expose the port the app runs on (Render defaults to using the PORT env variable)
ENV PORT=8000
EXPOSE $PORT

# Command to run the application using gunicorn for production capabilities
CMD sh -c "gunicorn -b 0.0.0.0:${PORT} main:app"

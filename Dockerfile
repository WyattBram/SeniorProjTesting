FROM python:3.13.2-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    docker.io \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy API server code
COPY api_server.py .

# Create temp directories
RUN mkdir -p temp_uploads image_container/input

# Expose port
EXPOSE 8000

# Run the API server
CMD ["python", "api_server.py"]

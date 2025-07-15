# Build stage
FROM python:3.11-slim as builder

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
COPY ../requirements.txt ../requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Runtime stage
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy Python dependencies from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY . ./api/
COPY ../streaming_response.py ./
COPY ../daytona_manager_refactored.py ./
COPY ../daytona_manager_cleaned.py ./
COPY ../daytona_manager.py ./
COPY ../permission_manager.py ./
COPY ../enhanced_cli.py ./

# Set environment variables
ENV PYTHONPATH=/app:$PYTHONPATH
ENV API_HOST=0.0.0.0
ENV API_PORT=8000

# Expose port
EXPOSE 8000

# Run the application
CMD ["python", "api/main.py"]
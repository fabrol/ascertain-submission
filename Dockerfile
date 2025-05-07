FROM python:3.11-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libpq-dev && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY pyproject.toml ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir hatch && \
    pip install --no-cache-dir -e .

# Production stage
FROM python:3.11-slim AS production

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends libpq5 && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder stage
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY . .

# Copy startup scripts
COPY wait-for-it.sh docker-entrypoint.sh ./
RUN chmod +x wait-for-it.sh docker-entrypoint.sh

# Set environment variables
ENV PYTHONPATH=/app
ENV PORT=8000

EXPOSE 8000

# Use the entrypoint script
ENTRYPOINT ["./docker-entrypoint.sh"]

# Development stage
FROM builder AS development

WORKDIR /app

# Install development dependencies
RUN pip install --no-cache-dir -e ".[dev]"

# Copy application code
COPY . .

# Copy startup scripts
COPY wait-for-it.sh docker-entrypoint.sh ./
RUN chmod +x wait-for-it.sh docker-entrypoint.sh

# Set environment variables
ENV PYTHONPATH=/app
ENV PORT=8000
ENV ENVIRONMENT=development

EXPOSE 8000

# Use the entrypoint script
ENTRYPOINT ["./docker-entrypoint.sh"] 
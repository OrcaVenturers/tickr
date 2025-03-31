# Use Python slim-buster for a lightweight base
FROM python:3.11-slim-buster

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy only the requirements file first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy credentials.json first (will be overridden if mounted)
COPY credentials.json .

# Copy the application code
COPY . .

# Set environment variables for proper terminal output and NinjaTrader connection
ENV PYTHONUNBUFFERED=1 \
    COLUMNS=200 \
    LINES=50 \
    TERM=xterm-256color \
    CONFIG_FILE=/app/credentials.json \
    NT_HOST=host.docker.internal \
    NT_PORT=36973

# Create entrypoint script to handle .env file and set up host network
RUN echo '#!/bin/sh\n\
if [ -f .env ]; then\n\
    export $(cat .env | xargs)\n\
fi\n\
\n\
# Set terminal width for proper table formatting\n\
if [ -t 1 ]; then\n\
    stty cols 200\n\
fi\n\
\n\
# Add host.docker.internal to hosts if it doesn't exist (Linux compatibility)\n\
if ! grep -q "host.docker.internal" /etc/hosts; then\n\
    DOCKER_INTERNAL_HOST="$(ip route | awk '"'"'/default/ { print $3 }'"'"')"\n\
    echo "$DOCKER_INTERNAL_HOST host.docker.internal" >> /etc/hosts\n\
fi\n\
\n\
exec "$@"' > /app/entrypoint.sh \
    && chmod +x /app/entrypoint.sh

# Set the entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]

# Default command (can be overridden)
CMD ["python", "-m", "tickr.strategies.fibonacci.run", "production"]


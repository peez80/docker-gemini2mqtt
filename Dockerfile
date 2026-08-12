FROM python:3.12-slim

LABEL org.opencontainers.image.title="gemini2mqtt" \
    org.opencontainers.image.description="Bridge between MQTT and Google Gemini API" \
    org.opencontainers.image.source="https://github.com/peez80/docker-gemini2mqtt"

WORKDIR /app

# Install system dependencies & agy CLI
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && curl -fsSL https://antigravity.google/cli/install.sh | bash \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

ENV PATH="/root/.local/bin:${PATH}"

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY *.py ./

ENV PYTHONUNBUFFERED=1

ENTRYPOINT ["python", "main.py"]

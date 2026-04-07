# ── Stage 1: Install Gemini CLI via npm ──────────────────────────────────────
FROM node:22-slim AS gemini-builder

RUN npm install -g @google/gemini-cli

# ── Stage 2: Final Python image ───────────────────────────────────────────────
FROM python:3.12-slim

LABEL org.opencontainers.image.title="gemini2mqtt" \
    org.opencontainers.image.description="Bridge between MQTT and Gemini AI via Gemini CLI" \
    org.opencontainers.image.source="https://github.com/phili/docker-ai2mqtt"

# Copy Gemini CLI from the builder stage
COPY --from=gemini-builder /usr/local/lib/node_modules /usr/local/lib/node_modules
COPY --from=gemini-builder /usr/local/bin/node /usr/local/bin/node

# Create a wrapper script so 'gemini' is on PATH
RUN echo '#!/bin/sh\nexec node /usr/local/lib/node_modules/@google/gemini-cli/bundle/gemini.js "$@"' \
    > /usr/local/bin/gemini && chmod +x /usr/local/bin/gemini

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY gemini2mqtt.py .

ENV PYTHONUNBUFFERED=1

ENTRYPOINT ["python", "gemini2mqtt.py"]

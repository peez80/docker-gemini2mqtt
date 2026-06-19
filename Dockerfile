FROM python:3.12-slim

LABEL org.opencontainers.image.title="gemini2mqtt" \
    org.opencontainers.image.description="Bridge between MQTT and Google Gemini API" \
    org.opencontainers.image.source="https://github.com/peez80/docker-gemini2mqtt"

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY gemini2mqtt.py .

ENV PYTHONUNBUFFERED=1

ENTRYPOINT ["python", "gemini2mqtt.py"]

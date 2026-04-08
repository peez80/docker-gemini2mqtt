# gemini2mqtt

> An MQTT-to-Gemini-AI bridge service that receives prompts via MQTT, forwards them to Gemini AI, and publishes the response back via MQTT.

---

## How it works

```
MQTT Broker
  │
  ├─► Topic: MQTT_PROMPT_TOPIC   (incoming)
  │       Message format: "response_topic|prompt"
  │
  └─► Topic: <response_topic>    (outgoing)
          Content: Gemini AI response
```

### Message format

Incoming messages must contain two `|`-separated fields:

| Field | Description | Example |
|---|---|---|
| `response_topic` | MQTT topic to publish the response to | `home/ai/response` |
| `prompt` | The prompt to send to Gemini AI | `What is 2+2?` |

**Example:**
```
home/ai/response|What is the capital of Bavaria?
```

---

## Configuration (environment variables)

All settings are configured via environment variables. Copy `.env.example` to `.env` and adjust the values:

```bash
cp .env.example .env
```

| Variable | Default | Required | Description |
|---|---|---|---|
| `MQTT_HOST` | `localhost` | – | MQTT broker hostname |
| `MQTT_PORT` | `1883` | – | MQTT broker port |
| `MQTT_USERNAME` | – | – | MQTT username |
| `MQTT_PASSWORD` | – | – | MQTT password |
| `MQTT_PROMPT_TOPIC` | `gemini2mqtt/prompt` | **Yes** | Topic for incoming prompts |
| `GEMINI_CLI_PATH` | `gemini` | – | Path to the Gemini CLI binary |
| `GEMINI_MODEL` | `gemini-3-flash-preview` | – | Gemini model |
| `GEMINI_MAX_CONCURRENT` | `2` | – | Max. simultaneous Gemini calls |
| `GEMINI_TIMEOUT_SECONDS` | `120` | – | Timeout for Gemini CLI calls in seconds |

---

## Deployment with Docker

### Quick start

```bash
# 1. Create .env
cp .env.example .env
# (adjust values in .env)

# 2. Build image and start container
docker compose up -d --build
```

### View logs

```bash
docker compose logs -f gemini2mqtt
```

### Stop container

```bash
docker compose down
```

---

## Local development (without Docker)

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
cp .env.example .env
# adjust .env as needed

# Start
python gemini2mqtt.py
```

> **Prerequisite:** The Gemini CLI must be installed locally and available on the `PATH`.  
> Installation: `npm install -g @google/gemini-cli`

---

## Authentication (Gemini CLI)

To authenticate with the Gemini API, credentials must be generated once inside a container and persisted to a local directory:

```bash
# Create a local directory for credentials
mkdir -p /path/to/credentials-directory

# Start container interactively with Gemini CLI and mount the directory
docker run -it --rm --entrypoint gemini \
  -v "/path/to/credentials-directory:/root/.gemini" \
  peez/gemini2mqtt
```

In the interactive CLI:

1. Navigate to **"Sign in with Google"** using the arrow keys and confirm.
2. Copy the displayed URL and open it in your browser.
3. Complete the Google auth flow and paste the displayed code back into the CLI.
4. After successful authentication, credentials are saved to `/path/to/credentials-directory`.

Mount this directory as a volume in `docker-compose.yml` so the service uses the stored credentials on startup.

---

## Project structure

```
docker-ai2mqtt/
├── gemini2mqtt.py       # Main application
├── Dockerfile           # Docker image (Python + Gemini CLI)
├── docker-compose.yml   # Compose configuration
├── requirements.txt     # Python dependencies
├── .env.example         # Environment variable template
├── .dockerignore
├── .gitignore
└── spec.md              # Project specification
```

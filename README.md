# gemini2mqtt

![Docker Image Versioning](https://img.shields.io/badge/docker-image-blue)
![Multi-Arch](https://img.shields.io/badge/multi--arch-linux%2Farm64-orange)
![Python](https://img.shields.io/badge/python-3.10+-blue)
![MQTT](https://img.shields.io/badge/mqtt-v5-red)
![License](https://img.shields.io/badge/license-MIT-green)

https://github.com/peez80/docker-gemini2mqtt

> An MQTT-to-Gemini-AI bridge service that receives prompts via MQTT, forwards them to Google Gemini API, and publishes the response back via MQTT.

---

## How it works

```
MQTT Broker
  │
  ├─► Topic: MQTT_PROMPT_TOPIC   (incoming)
  │       Message format: "response_topic|prompt"
  │
  └─► Topic: <response_topic>    (outgoing)
          Message format: "response_topic|gemini_answer"
```

### Message format

#### Incoming (Prompt)

You can send incoming messages in two formats: **String (Pipe-separated)** or **JSON**.

**Option A: Pipe-separated string (Default)**

Incoming messages must contain two `|`-separated fields:

| Field | Description | Example |
|---|---|---|
| `response_topic` | MQTT topic to publish the response to | `home/ai/response` |
| `prompt` | The prompt to send to Gemini AI | `What is 2+2?` |

**Example:**
```
home/ai/response|What is the capital of Bavaria?
```

**Option B: JSON Payload (Supports File Uploads)**

If you want to attach local documents or images to the prompt, use the JSON format:

```json
{
  "response_topic": "home/ai/response",
  "prompt": "What is the summary of this document?",
  "files": ["/data/docs/report.pdf"]
}
```

> **Note on Files:** The file paths must exist locally on the machine running `gemini2mqtt`. If you are running via Docker, make sure to mount a local directory into the container via `volumes` in your `docker-compose.yml` (e.g. `- /my/local/docs:/data/docs`).

#### Outgoing (Response)

The response is published to `<response_topic>` in the same `|`-separated format:

| Field | Description | Example |
|---|---|---|
| `response_topic` | The topic the response was published to | `home/ai/response` |
| `gemini_answer` | The Gemini AI response text | `The capital of Bavaria is Munich.` |

**Example:**
```
home/ai/response|The capital of Bavaria is Munich.
```

---

## Configuration (environment variables)

All settings are configured via environment variables. Copy `.env.example` to `.env` and adjust the values:

```bash
cp .env.example .env
```

| Variable | Default | Required | Description |
|---|---|---|---|
| `LOG_LEVEL` | `INFO` | – | Application log level |
| `MQTT_HOST` | `localhost` | – | MQTT broker hostname |
| `MQTT_PORT` | `1883` | – | MQTT broker port |
| `MQTT_USERNAME` | – | – | MQTT username |
| `MQTT_PASSWORD` | – | – | MQTT password |
| `MQTT_PROMPT_TOPIC` | `gemini2mqtt/prompt` | **Yes** | Topic for incoming prompts |
| `GEMINI_API_KEY` | – | **Yes** | Your Gemini API Key from Google AI Studio |
| `GEMINI_MODEL` | `gemini-3.1-flash-lite` | – | Gemini model to use |
| `GEMINI_MAX_CONCURRENT` | `2` | – | Max. simultaneous Gemini calls |
| `GEMINI_TIMEOUT_SECONDS` | `120` | – | Timeout for Gemini API calls in seconds |
| `GEMINI_RETRY_COUNT` | `3` | – | Max. number of attempts per Gemini call (min. 1) |
| `AI_BACKEND` | `gemini` | – | Select AI backend: `gemini` or `vertex` |
| `VERTEX_GOOGLE_CLOUD_PROJECT` | – | **Vertex** | GCP project ID (only for Vertex AI setup) |
| `VERTEX_GOOGLE_CLOUD_LOCATION` | `global` | **Vertex** | GCP region/location (only for Vertex AI setup) |
| `GOOGLE_APPLICATION_CREDENTIALS`| – | **Vertex** | Container path to GCP service account key JSON |

---

## Deployment with Docker

### Quick start

```bash
# 1. Create .env
cp .env.example .env
# (adjust values in .env, make sure to set GEMINI_API_KEY)

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
# adjust .env as needed, setting GEMINI_API_KEY

# Start
uv run python main.py
```

---

## Authentication

### Standard Mode (Google AI Studio API Key)

The default and easiest way to authenticate is by obtaining a free API key from [Google AI Studio](https://aistudio.google.com/).
1. Generate an API Key.
2. Set `GEMINI_API_KEY=your_api_key_here` in your `.env` file.

### Vertex AI API (Alternative)

#### When to use Vertex AI?

| | Standard (AI Studio) | Vertex AI |
|---|---|---|
| Quick setup | ✅ | — |
| Free tier | ✅ | — |
| **Paid API (billing required)** | — | ✅ |
| Production server / CI | — | ✅ |
| Data not used for model training | — | ✅ |
| GDPR / data residency in EU | — | ✅ (region `europe-west4`) |
| Higher quotas & SLA | — | ✅ |

**Standard mode** is the easiest setup and works well for personal or home-server use.

**Vertex AI** is a paid Google Cloud API — billing must be enabled on your GCP project.
Use it when data privacy is a requirement (requests are not used for training),
when you need guaranteed quotas beyond the free tier, or when running in a
production / enterprise environment.

#### Prerequisites for Vertex AI

1. Create (or reuse) a [GCP project](https://console.cloud.google.com/) with billing enabled
2. Enable the **Vertex AI API**:
   ```
   gcloud services enable aiplatform.googleapis.com --project=<PROJECT_ID>
   ```
3. Create a **Service Account** and grant it the `Vertex AI User` role:
   ```
   gcloud iam service-accounts create gemini2mqtt \
     --display-name="gemini2mqtt" --project=<PROJECT_ID>

   gcloud projects add-iam-policy-binding <PROJECT_ID> \
     --member="serviceAccount:gemini2mqtt@<PROJECT_ID>.iam.gserviceaccount.com" \
     --role="roles/aiplatform.user"
   ```
4. Download the **JSON key**:
   ```
   gcloud iam service-accounts keys create vertex_key.json \
     --iam-account=gemini2mqtt@<PROJECT_ID>.iam.gserviceaccount.com
   ```
5. Populate `.env` and start the Compose stack:
   ```bash
   cp .env.example .env
   # Set AI_BACKEND=vertex, VERTEX_GOOGLE_CLOUD_PROJECT
   # Open docker-compose.yml and uncomment the volume mount for the key file
   docker compose up -d --build
   ```

---

## Testing

The project uses `pytest` and `testcontainers` for robust unit and integration testing with an embedded Mosquitto broker.

We recommend using [uv](https://docs.astral.sh/uv/) to run the tests, as it automatically manages the Python version and creates an isolated virtual environment (`venv`) lightning-fast.

1. Install `uv` (if not already installed).
2. **Run fast unit tests (Mocked API):**
   ```bash
   uv run pytest -v
   ```
   *This runs fast, free tests without hitting the real Google Gemini API.*

3. **Run End-to-End integration tests (Real API):**
   ```bash
   uv run pytest -v --run-e2e
   ```
   *This requires a valid `GEMINI_API_KEY` in your `.env` file and will perform real requests against the Google servers (consuming API quotas).*

> *(Testing requires a running Docker daemon for `testcontainers` to spin up the mock MQTT broker).*
---

## Project structure

```
docker-ai2mqtt/
├── main.py              # Main application orchestrator
├── config.py            # Configuration handling
├── ai_client.py         # Google Gemini SDK logic
├── mqtt_client.py       # MQTT connection and parsing
├── task_manager.py      # Background task and queue tracking
├── Dockerfile           # Docker image (Python only)
├── docker-compose.yml           # Compose configuration
├── requirements.txt     # Python dependencies
├── .env.example         # Environment variable template
├── .dockerignore
├── .gitignore
└── spec.md              # Project specification
```

---

## Docker Image Versioning

The image `peez/gemini2mqtt` is built automatically on every merge to the `main` branch
and published to Docker Hub as a multi-arch image (`linux/amd64` & `linux/arm64`).

### Available tags

| Tag | Example | Description |
|---|---|---|
| `latest` | `peez/gemini2mqtt:latest` | Always points to the most recent build |
| `YYYYMMDDhhmm` | `peez/gemini2mqtt:202604091830` | Immutable timestamp snapshot (UTC) |

### Which tag should I use?

- **`latest`** – suitable for private / home-server use when you always want the newest version.
  Works well in combination with tools like [Watchtower](https://containrrr.dev/watchtower/) for automatic updates.
- **Timestamp tag** – recommended for production or reproducible deployments where you want to pin
  a specific, tested version and control updates explicitly.

### Pulling a specific version

```bash
# Always latest
docker pull peez/gemini2mqtt:latest

# Specific snapshot
docker pull peez/gemini2mqtt:202604091830
```

### Updating

```bash
# Pull the new image and restart the container
docker compose pull
docker compose up -d
```

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
          Message format: "response_topic|gemini_answer"
```

### Message format

#### Incoming (Prompt)

Incoming messages must contain two `|`-separated fields:

| Field | Description | Example |
|---|---|---|
| `response_topic` | MQTT topic to publish the response to | `home/ai/response` |
| `prompt` | The prompt to send to Gemini AI | `What is 2+2?` |

**Example:**
```
home/ai/response|What is the capital of Bavaria?
```

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
| `MQTT_HOST` | `localhost` | – | MQTT broker hostname |
| `MQTT_PORT` | `1883` | – | MQTT broker port |
| `MQTT_USERNAME` | – | – | MQTT username |
| `MQTT_PASSWORD` | – | – | MQTT password |
| `MQTT_PROMPT_TOPIC` | `gemini2mqtt/prompt` | **Yes** | Topic for incoming prompts |
| `GEMINI_CLI_PATH` | `gemini` | – | Path to the Gemini CLI binary |
| `GEMINI_MODEL` | `gemini-3-flash-preview` | – | Gemini model |
| `GEMINI_MAX_CONCURRENT` | `2` | – | Max. simultaneous Gemini calls |
| `GEMINI_TIMEOUT_SECONDS` | `120` | – | Timeout for Gemini CLI calls in seconds |
| `GEMINI_RETRY_COUNT` | `3` | – | Max. number of attempts per Gemini call (min. 1) |
| `GEMINI_KEEPALIVE_ENABLED` | `true` | – | Set to `false` to disable the daily Gemini keepalive ping |
| `GOOGLE_CLOUD_PROJECT` | – | **Vertex** | GCP project ID (only for Vertex AI setup) |
| `GOOGLE_CLOUD_LOCATION` | `global` | **Vertex** | GCP region/location (only for Vertex AI setup) |
| `VERTEX_CREDENTIAL_FILE` | `~/.gemini_vertex/vertex_key.json` | **Vertex** | Host path to GCP service account key JSON |

> **Note on the keepalive ping:** The service sends a daily dummy prompt to Gemini at noon (UTC) to keep the authentication token alive. This is only needed when using the **standard Gemini CLI** setup, which relies on a refresh token that can expire over time. When using **Vertex AI**, authentication is handled via a service account key that does not expire — the ping is therefore not needed and should be disabled (`GEMINI_KEEPALIVE_ENABLED=false`) to avoid unnecessary API calls and costs. The Vertex AI Compose files set this to `false` by default.

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

## Vertex AI API (Alternative)

### When to use Vertex AI?

| | Standard (Gemini CLI) | Vertex AI |
|---|---|---|
| Quick setup | ✅ | — |
| Free tier / personal use | ✅ | — |
| Uses your Google account quotas (incl. free quota) | ✅ | — |
| **Paid API (billing required)** | — | ✅ |
| Production server / CI | — | ✅ |
| Data not used for model training | — | ✅ |
| GDPR / data residency in EU | — | ✅ (region `europe-west4`) |
| Higher quotas & SLA | — | ✅ |

**Standard mode** authenticates via your Google account and uses its associated
quotas — including any free tier limits. This is the easiest setup and works well
for personal or home-server use.

**Vertex AI** is a paid Google Cloud API — billing must be enabled on your GCP project.
Use it when data privacy is a requirement (requests are not used for training),
when you need guaranteed quotas beyond the free tier, or when running in a
production / enterprise environment.

### Prerequisites

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
5. Populate `.env` and start the Vertex AI Compose stack:
   ```bash
   cp .env.example .env
   # Set GOOGLE_CLOUD_PROJECT and VERTEX_CREDENTIAL_FILE
   docker compose -f docker-compose-vertexapi.yml up -d --build
   ```

---

## Project structure

```
docker-ai2mqtt/
├── gemini2mqtt.py       # Main application
├── Dockerfile           # Docker image (Python + Gemini CLI)
├── docker-compose.yml           # Compose configuration (standard / Gemini CLI auth)
├── docker-compose-vertexapi.yml # Compose configuration (Vertex AI / service account)
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

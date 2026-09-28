# gemini2mqtt

![Docker Image Versioning](https://img.shields.io/badge/docker-image-blue)
![Multi-Arch](https://img.shields.io/badge/multi--arch-linux%2Farm64-orange)
![Python](https://img.shields.io/badge/python-3.10+-blue)
![MQTT](https://img.shields.io/badge/mqtt-v5-red)
![License](https://img.shields.io/badge/license-MIT-green)

https://github.com/peez80/docker-gemini2mqtt

> An MQTT bridge service connecting to Google Gemini AI via **Google AI Studio API**, **Google Cloud Vertex AI**, or the **Google Antigravity CLI (`agy`)**.

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
| `AI_BACKEND` | `gemini` | – | Select AI backend: `gemini`, `vertex`, or `agy` |
| `VERTEX_GOOGLE_CLOUD_PROJECT` | – | **Vertex** | GCP project ID (only for Vertex AI setup) |
| `VERTEX_GOOGLE_CLOUD_LOCATION` | `global` | **Vertex** | GCP region/location (only for Vertex AI setup) |
| `GOOGLE_APPLICATION_CREDENTIALS`| – | **Vertex** | Container path to GCP service account key JSON |
| `AGY_BINARY_PATH` | `agy` | – | Path to Antigravity CLI binary |
| `AGY_MODEL` | – | – | Model override for agy CLI (e.g. `gemini-3.6-flash-high`) |
| `AGY_EFFORT` | – | – | Reasoning effort for agy CLI (`low`, `medium`, `high`) |
| `AGY_TIMEOUT_SECONDS` | `120` | – | Timeout for agy CLI calls in seconds |
| `AGY_DANGEROUSLY_SKIP_PERMISSIONS`| `true` | – | Auto-approve tool permissions for headless MQTT execution |
| `AGY_CONCURRENT_REQUEST_DELAY_SECONDS` | `5.0` | – | Min. delay in seconds between starting concurrent agy CLI requests |


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

## Authentication & Backend Selection

`gemini2mqtt` supports three distinct AI backends depending on your infrastructure and privacy requirements:

| Feature / Criteria | Standard (AI Studio) | Vertex AI (GCP) | Antigravity CLI (`agy`) |
|---|---|---|---|
| **Primary Use Case** | Quick setup, personal projects | Enterprise, data compliance | Local agent workflows, reasoning control |
| **Authentication** | API Key (`GEMINI_API_KEY`) | Service Account Key JSON | OAuth Token (`~/.gemini/...`) |
| **Pricing / Quota** | Free tier (rate-limited) | Paid (GCP Project Billing) | Google Account / Antigravity tier |
| **Data Training** | Subject to AI Studio terms | ❌ Never used for training | Antigravity account terms |
| **GDPR / Region Control** | Global endpoints | ✅ Region pinning (e.g. `europe-west4`) | Managed by Antigravity CLI |
| **Reasoning Effort Control** | Default model reasoning | Default model reasoning | ✅ (`--effort low / medium / high`) |
| **Tool / Permission Approval** | Direct API | Direct API | ✅ Auto-approved (`--dangerously-skip-permissions`) |
| **Local File Attachments** | Google AI Files API | Inline Bytes (Base64) | Local workspace file context |

---

### Option 1: Standard Mode (Google AI Studio API Key)

The default and easiest way to authenticate is by obtaining an API key from [Google AI Studio](https://aistudio.google.com/):
1. Create a free API Key in Google AI Studio.
2. Set `GEMINI_API_KEY=your_api_key_here` in your `.env` file.
3. Keep `AI_BACKEND=gemini` (default).

---

### Option 2: Vertex AI API (Google Cloud Platform)

Vertex AI is recommended for enterprise setups with strict data residency requirements (EU data hosting) and SLA guarantees:

1. Create (or reuse) a [GCP project](https://console.cloud.google.com/) with billing enabled.
2. Enable the **Vertex AI API**:
   ```bash
   gcloud services enable aiplatform.googleapis.com --project=<PROJECT_ID>
   ```
3. Create a **Service Account** and grant it the `Vertex AI User` role:
   ```bash
   gcloud iam service-accounts create gemini2mqtt \
     --display-name="gemini2mqtt" --project=<PROJECT_ID>

   gcloud projects add-iam-policy-binding <PROJECT_ID> \
     --member="serviceAccount:gemini2mqtt@<PROJECT_ID>.iam.gserviceaccount.com" \
     --role="roles/aiplatform.user"
   ```
4. Download the **JSON key**:
   ```bash
   gcloud iam service-accounts keys create vertex_key.json \
     --iam-account=gemini2mqtt@<PROJECT_ID>.iam.gserviceaccount.com
   ```
5. Configure `.env` and `docker-compose.yml`:
   ```bash
   AI_BACKEND=vertex
   VERTEX_GOOGLE_CLOUD_PROJECT=your-project-id
   VERTEX_GOOGLE_CLOUD_LOCATION=global  # or europe-west4, us-central1, etc.
   GOOGLE_APPLICATION_CREDENTIALS=/app/vertex_key.json
   ```

---

### Option 3: Antigravity CLI (`agy`) Backend

You can use the **Google Antigravity CLI (`agy`)** as an execution backend. In this mode, incoming MQTT prompts are passed non-interactively to `agy -p "<prompt>"` via subprocess execution with automatic retry handling, configurable reasoning effort, and local file context support.

#### 1. Local Installation & First Login
If not already installed on your host machine:
```bash
# Install the agy CLI
curl -fsSL https://antigravity.google/cli/install.sh | bash

# Run agy once to complete the browser-based login flow
agy
```
Upon successful login, `agy` stores its session token in `~/.gemini/antigravity-cli/antigravity-oauth-token`.

#### 2. Authentication Concept: Volume-Mount vs. CI Secret
- **Local & Docker Compose (Volume Mount)**:
  Mount your local `${HOME}/.gemini` directory into the container. `gemini2mqtt` running inside Docker will access your local `antigravity-oauth-token` automatically.
- **GitHub Actions / CI (`ANTIGRAVITY_OAUTH_TOKEN`)**:
  In CI environments where no host folder exists, the *text content* of `~/.gemini/antigravity-cli/antigravity-oauth-token` is passed as a repository secret. The CI workflow writes this token directly to `/root/.gemini/antigravity-cli/antigravity-oauth-token` during test execution.

#### 3. Configuration (`.env`)
```bash
AI_BACKEND=agy
AGY_BINARY_PATH=agy
AGY_MODEL=gemini-3.6-flash-high       # Optional model override
AGY_EFFORT=high                      # Reasoning effort: low, medium, or high
AGY_TIMEOUT_SECONDS=120              # Max timeout per CLI prompt execution
AGY_DANGEROUSLY_SKIP_PERMISSIONS=true # Auto-approve tool calls for headless MQTT execution
AGY_CONCURRENT_REQUEST_DELAY_SECONDS=5.0 # Stagger concurrent agy process starts to prevent token race conditions
```

#### 4. Docker Compose Setup for `agy`
```yaml
services:
  gemini2mqtt:
    image: peez/gemini2mqtt:latest
    container_name: gemini2mqtt
    restart: unless-stopped
    env_file:
      - .env
    environment:
      AI_BACKEND: "agy"
      AGY_MODEL: "gemini-3.6-flash-high"
      AGY_EFFORT: "high"
      AGY_DANGEROUSLY_SKIP_PERMISSIONS: "true"
      AGY_CONCURRENT_REQUEST_DELAY_SECONDS: "5.0"
    volumes:
      # Mount host credentials into the container
      - "${HOME}/.gemini:/root/.gemini"
      # Optional: mount local documents directory for file attachment prompts
      - "/path/to/docs:/data/docs"
```

#### 5. Concurrency & Staggered Start (OAuth Race Condition Protection)
Google OAuth 2.0 enforces Refresh Token Rotation. If multiple `agy` CLI processes start simultaneously with an expired or expiring access token, they attempt to refresh the session concurrently. Google rotates the refresh token on the first request and revokes the session on subsequent requests using the old token (`invalid_grant` / "token revoked").

To prevent this while preserving full parallel throughput:
- `gemini2mqtt` automatically staggers the **start time** of concurrent `agy` CLI requests by `AGY_CONCURRENT_REQUEST_DELAY_SECONDS` (default: `5.0`s).
- Once started, requests execute in **parallel** up to the configured `GEMINI_MAX_CONCURRENT` limit.
- Requests arriving after idle periods start immediately with zero delay.



---

## Testing & CI

The project uses `pytest` and `testcontainers` for robust unit and integration testing with an embedded Mosquitto broker.

### Running tests in Docker (Recommended)

To mirror the production environment and CI test execution:

1. **Build the test image:**
   ```bash
   docker build -t gemini2mqtt:test .
   ```

2. **Run Unit Tests (Mocked API):**
   ```bash
   docker run --rm \
     -v /var/run/docker.sock:/var/run/docker.sock \
     -v /root/.gemini:/root/.gemini \
     -v $(pwd):/app \
     -w /app \
     --entrypoint bash \
     gemini2mqtt:test \
     -c "pip install uv && uv run pytest -v -m 'not e2e'"
   ```

3. **Run End-to-End integration tests (Real AI Backends):**
   ```bash
   docker run --rm \
     -v /var/run/docker.sock:/var/run/docker.sock \
     -v /root/.gemini:/root/.gemini \
     -v $(pwd):/app \
     -w /app \
     --entrypoint bash \
     gemini2mqtt:test \
     -c "pip install uv && uv run pytest -v --run-e2e"
   ```

### GitHub Actions CI Secrets

In GitHub Actions, the test suite is executed in the `gemini2mqtt:test` container. You can optionally configure the following Repository Secrets to run live E2E tests in CI:

| Secret | Description | Setup Command / Origin |
|---|---|---|
| `GEMINI_API_KEY` | Gemini API Key for running `test_real_gemini_api_integration` | [Google AI Studio](https://aistudio.google.com/app/apikey) |
| `ANTIGRAVITY_OAUTH_TOKEN` | Token JSON with `refresh_token` for running `test_real_agy_cli_integration` in CI | `python3 -c "import json, os; print(json.dumps(json.load(open(os.path.expanduser('~/.gemini/antigravity-cli/antigravity-oauth-token')))))"` |
| `DOCKERHUB_USERNAME` | Docker Hub Username (for build & push on `main`) | [Docker Hub](https://hub.docker.com/) |
| `DOCKERHUB_TOKEN` | Docker Hub Personal Access Token | [Docker Hub Security Settings](https://hub.docker.com/settings/security) |

*(If AI secrets are omitted, the respective E2E tests are automatically and cleanly skipped without failing the CI pipeline).*
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

# gemini2mqtt
## Short Summary
gemini2mqtt is a tool that receives prompts via MQTT and sends them to Google Gemini API. It then receives the response from Gemini AI and sends it back via MQTT.

## Features
- Receive Messages via MQTT:
    - Structure of the message: "response_topic|prompt"
    - response_topic: The topic to send the response to
    - prompt: The prompt to send to Gemini AI
- Send the prompt to Google Gemini API using the `google-genai` Python SDK, Vertex AI, or via Antigravity CLI (`agy`) shell calls.
- Send AI response back via MQTT to the defined response topic.


## Configuration
All necessary configuration is done via environment variables, e.g.

- MQTT server (`MQTT_HOST`, `MQTT_PORT`, `MQTT_USERNAME`, `MQTT_PASSWORD`, `MQTT_PROMPT_TOPIC`)
- AI Backend selector: `AI_BACKEND` (`gemini`, `vertex`, `agy`)
- GEMINI API Key (`GEMINI_API_KEY`) and Model (`GEMINI_MODEL`)
- Vertex AI Project & Location (`VERTEX_GOOGLE_CLOUD_PROJECT`, `VERTEX_GOOGLE_CLOUD_LOCATION`)
- Antigravity CLI (`AGY_BINARY_PATH`, `AGY_MODEL`, `AGY_EFFORT`, `AGY_TIMEOUT_SECONDS`, `AGY_DANGEROUSLY_SKIP_PERMISSIONS`, `AGY_CONCURRENT_REQUEST_DELAY_SECONDS`)


## Deployment
The tool is written in Python and can be deployed as a Docker container or run natively with `uv`.

## Usage
```bash
python main.py
```
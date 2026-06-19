# gemini2mqtt
## Short Summary
gemini2mqtt is a tool that receives prompts via MQTT and sends them to Google Gemini API. It then receives the response from Gemini AI and sends it back via MQTT.

## Features
- Receive Messages via MQTT:
    - Structure of the message: "response_topic|prompt"
    - response_topic: The topic to send the response to
    - prompt: The prompt to send to Gemini AI
- Send the prompt to Google Gemini API using the `google-genai` Python SDK.
- Send Geminis response back via MQTT to the defined response topic.


## Configuration
All necessary configuration is done via environment variables, e.g.

- MQTT server
- MQTT port
- MQTT username
- MQTT password
- MQTT topic for prompts
- GEMINI_API_KEY
- GEMINI_MODEL

## deployment
The Tool is written in python, deployed via a Docker Container.

## Usage
```bash
gemini2mqtt
```
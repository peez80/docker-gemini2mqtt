# gemini2mqtt
## Short Summary
gemini2mqtt is a tool that receives prompts via MQTT and sends them to Gemini AI via Gemini CLI. It then receives the response from Gemini AI and sends it back via MQTT.

## Features
- Receive Messages via MQTT:
    - Structure of the message: "response_topic|use_vertex_api|prompt"
    - response_topic: The topic to send the response to
    - use_vertex_api: Whether to use Vertex AI (true/false). In case of false, it uses the common gemini cli to use up the standard gemini AI (pro) quota. In case of true, it uses the vertex ai gemini cli to use up the vertex ai gemini quota, e.g. when the prompt contains sensitive data that might not be used e.g. for model training.
    - prompt: The prompt to send to Gemini AI
- Send the prompt  to gemini cli - if requested, to the vertex ai, otherwise the standard gemini api.
- Send Geminis response back via MQTT to the defined response topic.


## Configuration
All necessary configuration is done via environment variables, e.g.

- MQTT server
- MQTT port
- MQTT username
- MQTT password
- MQTT topic for prompts
- Gemini CLI path

## deployment
The Tool is written in python, deployed via a Docker Container. The docker image contains the gemini cli.

## Usage
```bash
gemini2mqtt
```
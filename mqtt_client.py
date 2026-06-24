import logging
import json
from typing import Callable, Optional

import paho.mqtt.client as mqtt
from config import AppConfig

logger = logging.getLogger(__name__)

def parse_message(payload: str) -> Optional[tuple[str, str, list[str]]]:
    """
    Parse the incoming MQTT message.
    Expected format: "response_topic|prompt" OR a JSON object.
    Returns (response_topic, prompt, files) or None on parse error.
    """
    payload_stripped = payload.strip()
    if payload_stripped.startswith("{") and payload_stripped.endswith("}"):
        try:
            data = json.loads(payload_stripped)
            response_topic = data.get("response_topic")
            prompt = data.get("prompt")
            if not response_topic or not prompt:
                logger.warning("JSON payload missing 'response_topic' or 'prompt': %r", payload)
                return None
            files = data.get("files", [])
            if not isinstance(files, list):
                files = [files]
            return str(response_topic), str(prompt), [str(f) for f in files]
        except json.JSONDecodeError as e:
            logger.warning("Invalid JSON payload: %s", e)
            return None

    parts = payload.split("|", 1)
    if len(parts) != 2:
        logger.warning("Invalid message format (expected 2 pipe-separated fields or JSON): %r", payload)
        return None
    response_topic, prompt = parts
    return response_topic.strip(), prompt.strip(), []


class MqttClient:
    def __init__(self, config: AppConfig):
        self.config = config
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        
        if self.config.mqtt_username:
            self.client.username_pw_set(self.config.mqtt_username, self.config.mqtt_password)

        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self.on_message
        
        self._message_callback: Optional[Callable[[str, str, list[str]], None]] = None

    def register_message_callback(self, callback: Callable[[str, str, list[str]], None]) -> None:
        self._message_callback = callback

    def _on_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code == 0:
            logger.info("Connected to MQTT broker at %s:%d", self.config.mqtt_host, self.config.mqtt_port)
            self.client.subscribe(self.config.mqtt_prompt_topic)
            logger.info("Subscribed to topic: %s", self.config.mqtt_prompt_topic)
        else:
            logger.error("MQTT connection failed with reason code: %s", reason_code)

    def _on_disconnect(self, client, userdata, disconnect_flags, reason_code, properties):
        if reason_code != 0:
            logger.warning("Unexpected disconnect (rc=%s). Reconnecting…", reason_code)

    def on_message(self, client, userdata, msg):
        payload = msg.payload.decode("utf-8", errors="replace")
        logger.info("Received message on topic '%s'", msg.topic)
        logger.debug("Payload: %r", payload)

        parsed = parse_message(payload)
        if parsed is None:
            return

        response_topic, prompt, files = parsed
        
        if self._message_callback:
            self._message_callback(response_topic, prompt, files)

    def publish(self, topic: str, payload: str) -> None:
        self.client.publish(topic, payload)
        logger.info("Response published to topic '%s'", topic)

    def start(self, background: bool = False) -> None:
        logger.info("Connecting to MQTT broker %s:%d …", self.config.mqtt_host, self.config.mqtt_port)
        self.client.connect(self.config.mqtt_host, self.config.mqtt_port, keepalive=60)
        
        if background:
            self.client.loop_start()
        else:
            self.client.loop_forever()

    def stop(self) -> None:
        logger.info("Shutting down MQTT client…")
        self.client.loop_stop()
        self.client.disconnect()

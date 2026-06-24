#!/usr/bin/env python3
"""
gemini2mqtt - Receives prompts via MQTT and forwards them to Gemini AI via google-genai SDK.
Message format: "response_topic|prompt"
"""

import os
import signal
import sys
import logging

from config import load_config, AppConfig
from ai_client import AIClient
from mqtt_client import MqttClient
from task_manager import TaskManager

log_level_str = os.environ.get("LOG_LEVEL", "INFO").upper()
log_level = getattr(logging, log_level_str, logging.INFO)

logging.basicConfig(
    level=log_level,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


class Gemini2MqttApp:
    def __init__(self, config: AppConfig):
        self.config = config
        
        self.task_manager = TaskManager(self.config.gemini_max_concurrent)
        self.ai_client = AIClient(self.config)
        self.mqtt_client = MqttClient(self.config)
        
        self.mqtt_client.register_message_callback(self.on_mqtt_message)

    def on_mqtt_message(self, response_topic: str, prompt: str, files: list[str]) -> None:
        logger.info("Forwarding prompt to AI API (response → '%s')", response_topic)
        
        def worker_fn():
            try:
                response = self.ai_client.generate_content(prompt, files=files, log_context=response_topic)
                payload = f"{response_topic}|{response}"
                self.mqtt_client.publish(response_topic, payload)
            except Exception as e:
                # _call_gemini_with_retry will log and return "ERROR: ..." on complete failure
                # so an unhandled exception here shouldn't happen unless unexpected,
                # but if it does, we can catch it.
                logger.error("Unhandled exception in AI worker task: %s", e)

        self.task_manager.submit_task(worker_fn)

    def start(self, background: bool = False):
        self.mqtt_client.start(background=background)

    def stop(self):
        logger.info("Shutting down…")
        self.mqtt_client.stop()
        self.task_manager.shutdown()


def main():
    config = load_config()
    app = Gemini2MqttApp(config)

    def _shutdown(signum, frame):
        logger.info("Received signal %d", signum)
        app.stop()
        sys.exit(0)

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)

    app.start(background=False)


if __name__ == "__main__":
    main()

import os
import sys
import logging
from typing import Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class AppConfig:
    mqtt_host: str
    mqtt_port: int
    mqtt_username: Optional[str]
    mqtt_password: Optional[str]
    mqtt_prompt_topic: str
    gemini_model: str
    gemini_max_concurrent: int
    gemini_timeout_seconds: int
    gemini_retry_count: int

def load_config() -> AppConfig:
    def get_env(name: str, default: Optional[str] = None, required: bool = False) -> str:
        value = os.environ.get(name, default)
        if required and not value:
            logger.error("Required environment variable '%s' is not set.", name)
            sys.exit(1)
        return value

    return AppConfig(
        mqtt_host=get_env("MQTT_HOST", "localhost"),
        mqtt_port=int(get_env("MQTT_PORT", "1883")),
        mqtt_username=get_env("MQTT_USERNAME"),
        mqtt_password=get_env("MQTT_PASSWORD"),
        mqtt_prompt_topic=get_env("MQTT_PROMPT_TOPIC", "gemini2mqtt/prompt", required=True),
        gemini_model=get_env("GEMINI_MODEL", "gemini-3.1-flash-lite"),
        gemini_max_concurrent=int(get_env("GEMINI_MAX_CONCURRENT", "2")),
        gemini_timeout_seconds=int(get_env("GEMINI_TIMEOUT_SECONDS", "120")),
        gemini_retry_count=max(1, int(get_env("GEMINI_RETRY_COUNT", "3"))),
    )

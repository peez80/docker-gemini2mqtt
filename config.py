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
    ai_backend: str
    vertex_project: Optional[str]
    vertex_location: Optional[str]
    agy_binary_path: str = "agy"
    agy_model: Optional[str] = None
    agy_effort: Optional[str] = None
    agy_timeout_seconds: int = 120
    agy_dangerously_skip_permissions: bool = True
    agy_concurrent_request_delay_seconds: float = 5.0

def load_config() -> AppConfig:
    def get_env(name: str, default: Optional[str] = None, required: bool = False) -> str:
        value = os.environ.get(name, default)
        if required and not value:
            logger.error("Required environment variable '%s' is not set.", name)
            sys.exit(1)
        return value

    ai_backend = get_env("AI_BACKEND", "gemini").lower()
    vertex_project = get_env("VERTEX_GOOGLE_CLOUD_PROJECT", required=(ai_backend == "vertex"))
    vertex_location = get_env("VERTEX_GOOGLE_CLOUD_LOCATION", "global")

    gemini_timeout_seconds = int(get_env("GEMINI_TIMEOUT_SECONDS", "120"))
    agy_timeout_seconds = int(get_env("AGY_TIMEOUT_SECONDS", str(gemini_timeout_seconds)))
    agy_skip_perms_str = get_env("AGY_DANGEROUSLY_SKIP_PERMISSIONS", "true").lower()
    agy_dangerously_skip_permissions = agy_skip_perms_str in ("true", "1", "yes")
    agy_concurrent_request_delay_seconds = max(0.0, float(get_env("AGY_CONCURRENT_REQUEST_DELAY_SECONDS", "5.0")))

    return AppConfig(
        mqtt_host=get_env("MQTT_HOST", "localhost"),
        mqtt_port=int(get_env("MQTT_PORT", "1883")),
        mqtt_username=get_env("MQTT_USERNAME"),
        mqtt_password=get_env("MQTT_PASSWORD"),
        mqtt_prompt_topic=get_env("MQTT_PROMPT_TOPIC", "gemini2mqtt/prompt", required=True),
        gemini_model=get_env("GEMINI_MODEL", "gemini-3.1-flash-lite"),
        gemini_max_concurrent=int(get_env("GEMINI_MAX_CONCURRENT", "2")),
        gemini_timeout_seconds=gemini_timeout_seconds,
        gemini_retry_count=max(1, int(get_env("GEMINI_RETRY_COUNT", "3"))),
        ai_backend=ai_backend,
        vertex_project=vertex_project,
        vertex_location=vertex_location,
        agy_binary_path=get_env("AGY_BINARY_PATH", "agy"),
        agy_model=get_env("AGY_MODEL"),
        agy_effort=get_env("AGY_EFFORT"),
        agy_timeout_seconds=agy_timeout_seconds,
        agy_dangerously_skip_permissions=agy_dangerously_skip_permissions,
        agy_concurrent_request_delay_seconds=agy_concurrent_request_delay_seconds,
    )

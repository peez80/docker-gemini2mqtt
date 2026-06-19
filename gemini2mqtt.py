#!/usr/bin/env python3
"""
gemini2mqtt - Receives prompts via MQTT and forwards them to Gemini AI via google-genai SDK.
Message format: "response_topic|prompt"
"""

import os
import logging
import signal
import sys
import concurrent.futures
import threading
import time
from typing import Optional
from dataclasses import dataclass

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

import paho.mqtt.client as mqtt
from google import genai
from google.genai import types

# ── Logging ──────────────────────────────────────────────────────────────────
log_level_str = os.environ.get("LOG_LEVEL", "INFO").upper()
log_level = getattr(logging, log_level_str, logging.INFO)

logging.basicConfig(
    level=log_level,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# ── Configuration ─────────────────────────────────────────────────────────────
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


# ── Task tracking (thread-safe) ───────────────────────────────────────────────
_tasks_lock = threading.Lock()
_pending_count: int = 0        # submitted to executor, not yet started
_active_tasks: dict[int, float] = {}  # task_id → monotonic start time
_task_id_counter: int = 0
_executor: Optional[concurrent.futures.ThreadPoolExecutor] = None


# ── Gemini helpers ────────────────────────────────────────────────────────────

def _on_retry_exhausted(retry_state) -> str:
    """Called by tenacity when all attempts are exhausted; returns the last error string."""
    last_exc = retry_state.outcome.exception()
    log_context = retry_state.kwargs.get("log_context", "")
    prefix = f"[Topic: {log_context}] " if log_context else ""
    config = retry_state.kwargs.get("config")
    retry_count = config.gemini_retry_count if config else 3
    logger.error(
        "%sGemini call failed on all %d attempts. Last error: %s",
        prefix, retry_count, last_exc,
    )
    return f"ERROR: {last_exc}"


def _before_sleep_custom_log(retry_state) -> None:
    """Custom logging during Tenacity retries to inject the contextual prefix."""
    log_context = retry_state.kwargs.get("log_context", "")
    prefix = f"[Topic: {log_context}] " if log_context else ""
    exc = retry_state.outcome.exception()
    
    logger.warning(
        "%sRetrying %s in %.2f seconds as it raised: %s",
        prefix,
        retry_state.fn.__name__,
        retry_state.next_action.sleep,
        exc,
    )

# Since tenacity decorators are evaluated at import time, we set a default max attempts
# but can optionally override it via retry state, or simply use a reasonably high default if we wanted.
# Here we use stop_after_attempt(10) as a safe upper bound, but we can dynamically stop it if needed.
# Actually, since GEMINI_RETRY_COUNT is dynamic, we'll wrap the logic.
@retry(
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(Exception),
    before_sleep=_before_sleep_custom_log,
    retry_error_callback=_on_retry_exhausted,
)
def _call_gemini_with_retry(prompt: str, config: AppConfig, log_context: str = "", retry_state=None) -> str:
    """Invoke the Gemini API and return the text response (with automatic retry)."""
    prefix = f"[Topic: {log_context}] " if log_context else ""
    
    if retry_state and retry_state.attempt_number > config.gemini_retry_count:
        raise Exception(f"Max retries ({config.gemini_retry_count}) exceeded")

    logger.debug("%sCalling Gemini API (model: %s)...", prefix, config.gemini_model)
    
    # Initialize the client. This automatically picks up GEMINI_API_KEY
    # or Vertex AI environment variables.
    client = genai.Client(
        http_options=types.HttpOptions(timeout=config.gemini_timeout_seconds * 1000)
    )
    
    response = client.models.generate_content(
        model=config.gemini_model,
        contents=prompt,
    )
    
    return response.text

def call_gemini(prompt: str, config: AppConfig, log_context: str = "") -> str:
    # We dynamically apply stop_after_attempt based on config
    return _call_gemini_with_retry.retry_with(
        stop=stop_after_attempt(config.gemini_retry_count)
    )(prompt=prompt, config=config, log_context=log_context)


# ── MQTT callbacks ────────────────────────────────────────────────────────────

def parse_message(payload: str) -> tuple[str, str] | None:
    """
    Parse the incoming MQTT message.
    Expected format: "response_topic|prompt"
    Returns (response_topic, prompt) or None on parse error.
    """
    parts = payload.split("|", 1)
    if len(parts) != 2:
        logger.warning("Invalid message format (expected 2 pipe-separated fields): %r", payload)
        return None
    response_topic, prompt = parts
    return response_topic.strip(), prompt.strip()


def on_connect(client, userdata, flags, reason_code, properties):
    config = userdata["config"]
    if reason_code == 0:
        logger.info("Connected to MQTT broker at %s:%d", config.mqtt_host, config.mqtt_port)
        client.subscribe(config.mqtt_prompt_topic)
        logger.info("Subscribed to topic: %s", config.mqtt_prompt_topic)
    else:
        logger.error("MQTT connection failed with reason code: %s", reason_code)


def on_disconnect(client, userdata, disconnect_flags, reason_code, properties):
    if reason_code != 0:
        logger.warning("Unexpected disconnect (rc=%s). Reconnecting…", reason_code)


def on_message(client, userdata, msg):
    payload = msg.payload.decode("utf-8", errors="replace")
    logger.info("Received message on topic '%s'", msg.topic)
    logger.debug("Payload: %r", payload)

    parsed = parse_message(payload)
    if parsed is None:
        return

    response_topic, prompt = parsed
    config = userdata["config"]

    global _pending_count, _task_id_counter
    with _tasks_lock:
        task_id = _task_id_counter
        _task_id_counter += 1
        _pending_count += 1

    if _executor is not None:
        _executor.submit(_handle_prompt, client, config, response_topic, prompt, task_id)


def _handle_prompt(client, config: AppConfig, response_topic: str, prompt: str, task_id: int) -> None:
    global _pending_count
    with _tasks_lock:
        _pending_count -= 1
        _active_tasks[task_id] = time.monotonic()

    logger.info("Forwarding prompt to Gemini (response → '%s')", response_topic)
    try:
        response = call_gemini(prompt, config=config, log_context=response_topic)
        payload = f"{response_topic}|{response}"
        client.publish(response_topic, payload)
        logger.info("Response published to topic '%s'", response_topic)
    finally:
        with _tasks_lock:
            _active_tasks.pop(task_id, None)


# ── Queue status logger ───────────────────────────────────────────────────────

QUEUE_STATUS_INTERVAL = 30  # seconds


def _queue_status_loop(stop_event: threading.Event) -> None:
    """Log queue status every 30 s while tasks are active or pending.
    Logs once more when the queue becomes empty."""
    was_busy = False
    while not stop_event.is_set():
        # Wait allows breaking early on shutdown
        if stop_event.wait(QUEUE_STATUS_INTERVAL):
            break
        
        now = time.monotonic()
        with _tasks_lock:
            active_durations = [round(now - t) for t in _active_tasks.values()]
            pending = _pending_count

        is_busy = bool(active_durations) or pending > 0
        if is_busy:
            durations_str = ", ".join(f"{d}s" for d in active_durations)
            logger.info(
                "Queue status: %d active (%s), %d queued",
                len(active_durations), durations_str, pending,
            )
            was_busy = True
        elif was_busy:
            logger.info("Queue status: 0 active, 0 queued (queue empty)")
            was_busy = False


# ── App lifecycle ─────────────────────────────────────────────────────────────

class Gemini2MqttApp:
    def __init__(self, config: AppConfig):
        self.config = config
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        # Pass config via userdata
        self.client.user_data_set({"config": self.config})
        
        if self.config.mqtt_username:
            self.client.username_pw_set(self.config.mqtt_username, self.config.mqtt_password)

        self.client.on_connect = on_connect
        self.client.on_disconnect = on_disconnect
        self.client.on_message = on_message
        
        self.stop_event = threading.Event()
        self.status_thread = None
        global _executor
        _executor = concurrent.futures.ThreadPoolExecutor(max_workers=self.config.gemini_max_concurrent)

    def start(self, background: bool = False):
        logger.info("Connecting to MQTT broker %s:%d …", self.config.mqtt_host, self.config.mqtt_port)
        self.client.connect(self.config.mqtt_host, self.config.mqtt_port, keepalive=60)
        
        self.status_thread = threading.Thread(target=_queue_status_loop, args=(self.stop_event,), daemon=True, name="queue-status")
        self.status_thread.start()

        if background:
            self.client.loop_start()
        else:
            self.client.loop_forever()

    def stop(self):
        logger.info("Shutting down…")
        self.stop_event.set()
        self.client.loop_stop()
        self.client.disconnect()
        global _executor
        if _executor is not None:
            _executor.shutdown(wait=False)


# ── Main ──────────────────────────────────────────────────────────────────────

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

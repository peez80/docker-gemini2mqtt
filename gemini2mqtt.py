#!/usr/bin/env python3
"""
gemini2mqtt - Receives prompts via MQTT and forwards them to Gemini AI via Gemini CLI.
Message format: "response_topic|prompt"
"""

import os
import subprocess
import logging
import signal
import sys
import concurrent.futures
import datetime
import threading
import time
from typing import Optional

from tenacity import (
    retry,
    retry_if_result,
    stop_after_attempt,
    wait_fixed,
    before_sleep_log,
)

import paho.mqtt.client as mqtt

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# ── Configuration (from environment variables) ────────────────────────────────
def get_env(name: str, default: Optional[str] = None, required: bool = False) -> str:
    value = os.environ.get(name, default)
    if required and not value:
        logger.error("Required environment variable '%s' is not set.", name)
        sys.exit(1)
    return value


MQTT_HOST = get_env("MQTT_HOST", "localhost")
MQTT_PORT = int(get_env("MQTT_PORT", "1883"))
MQTT_USERNAME = get_env("MQTT_USERNAME")
MQTT_PASSWORD = get_env("MQTT_PASSWORD")
MQTT_PROMPT_TOPIC = get_env("MQTT_PROMPT_TOPIC", "gemini2mqtt/prompt", required=True)
GEMINI_CLI_PATH = get_env("GEMINI_CLI_PATH", "gemini")
GEMINI_MODEL = get_env("GEMINI_MODEL", "gemini-3-flash-preview")
GEMINI_MAX_CONCURRENT = int(get_env("GEMINI_MAX_CONCURRENT", "2"))
GEMINI_TIMEOUT_SECONDS = int(get_env("GEMINI_TIMEOUT_SECONDS", "120"))
GEMINI_RETRY_COUNT     = max(1, int(get_env("GEMINI_RETRY_COUNT", "3")))
GEMINI_KEEPALIVE_ENABLED = get_env("GEMINI_KEEPALIVE_ENABLED", "true").strip().lower() not in ("false", "0", "no", "off")

_executor = concurrent.futures.ThreadPoolExecutor(max_workers=GEMINI_MAX_CONCURRENT)

# ── Task tracking (thread-safe) ───────────────────────────────────────────────
_tasks_lock = threading.Lock()
_pending_count: int = 0        # submitted to executor, not yet started
_active_tasks: dict[int, float] = {}  # task_id → monotonic start time
_task_id_counter: int = 0


# ── Gemini helpers ────────────────────────────────────────────────────────────

def _on_retry_exhausted(retry_state) -> str:
    """Called by tenacity when all attempts are exhausted; returns the last error string."""
    last_result = retry_state.outcome.result()
    logger.error(
        "Gemini call failed on all %d attempts. Last error: %s",
        GEMINI_RETRY_COUNT, last_result,
    )
    return last_result


@retry(
    stop=stop_after_attempt(GEMINI_RETRY_COUNT),
    wait=wait_fixed(5),
    retry=retry_if_result(lambda r: r.startswith("ERROR:")),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    retry_error_callback=_on_retry_exhausted,
)
def call_gemini(prompt: str) -> str:
    """Invoke the Gemini CLI and return the text response (with automatic retry)."""
    cmd = build_standard_command(prompt)

    logger.debug("Running command: %s", cmd)
    try:
        result = subprocess.run(
            cmd,
            input=prompt,
            capture_output=True,
            text=True,
            timeout=GEMINI_TIMEOUT_SECONDS,
        )
        if result.returncode != 0:
            logger.error("Gemini CLI error (rc=%d): %s", result.returncode, result.stderr.strip())
            return f"ERROR: Gemini CLI returned code {result.returncode}: {result.stderr.strip()}"

        response = result.stdout.strip()
        if not response:
            stderr_output = result.stderr.strip()
            error_msg = stderr_output if stderr_output else "Gemini CLI returned an empty response."
            logger.error("Gemini CLI returned empty stdout. stderr: %s", error_msg)
            return f"ERROR: {error_msg}"

        return response
    except subprocess.TimeoutExpired:
        logger.error("Gemini CLI timed out after %d s", GEMINI_TIMEOUT_SECONDS)
        return "ERROR: Gemini CLI timed out."
    except FileNotFoundError as exc:
        logger.error("Gemini CLI not found: %s", exc)
        return f"ERROR: Gemini CLI not found: {exc}"
    except Exception as exc:  # pylint: disable=broad-except
        logger.exception("Unexpected error calling Gemini CLI")
        return f"ERROR: {exc}"


def build_standard_command(prompt: str) -> list[str]:
    """Build command for the standard Gemini API."""
    return [
        GEMINI_CLI_PATH,
        "--model", GEMINI_MODEL,
        "-p", prompt,
    ]


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
    if reason_code == 0:
        logger.info("Connected to MQTT broker at %s:%d", MQTT_HOST, MQTT_PORT)
        client.subscribe(MQTT_PROMPT_TOPIC)
        logger.info("Subscribed to topic: %s", MQTT_PROMPT_TOPIC)
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

    global _pending_count, _task_id_counter
    with _tasks_lock:
        task_id = _task_id_counter
        _task_id_counter += 1
        _pending_count += 1

    _executor.submit(_handle_prompt, client, response_topic, prompt, task_id)


def _handle_prompt(client, response_topic: str, prompt: str, task_id: int) -> None:
    global _pending_count
    with _tasks_lock:
        _pending_count -= 1
        _active_tasks[task_id] = time.monotonic()

    logger.info("Forwarding prompt to Gemini (response → '%s')", response_topic)
    try:
        response = call_gemini(prompt)
        payload = f"{response_topic}|{response}"
        client.publish(response_topic, payload)
        logger.info("Response published to topic '%s'", response_topic)
    finally:
        now = time.monotonic()
        with _tasks_lock:
            _active_tasks.pop(task_id, None)
            active_durations = [round(now - t) for t in _active_tasks.values()]
            pending = _pending_count

        if active_durations:
            durations_str = ", ".join(f"{d}s" for d in active_durations)
            logger.info(
                "Queue status: %d active (%s), %d queued",
                len(active_durations), durations_str, pending,
            )
        else:
            logger.info("Queue status: 0 active, %d queued", pending)


# ── Daily keepalive ───────────────────────────────────────────────────────────

def _keepalive_loop() -> None:
    """Send a daily dummy prompt to Gemini at noon to keep the auth token alive."""
    while True:
        now = datetime.datetime.now(datetime.timezone.utc)
        next_noon = now.replace(hour=12, minute=0, second=0, microsecond=0)
        if next_noon <= now:
            next_noon += datetime.timedelta(days=1)
        sleep_seconds = (next_noon - now).total_seconds()
        logger.info(
            "Keepalive: next Gemini ping scheduled at %s UTC (in %.0f s)",
            next_noon.strftime("%Y-%m-%d %H:%M:%S"),
            sleep_seconds,
        )
        time.sleep(sleep_seconds)
        logger.info("Keepalive: sending daily Gemini ping…")
        response = call_gemini("ping")
        logger.info("Keepalive: Gemini ping done: %s", response)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

    if MQTT_USERNAME:
        client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)

    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message

    # Graceful shutdown on SIGTERM / SIGINT
    def _shutdown(signum, frame):
        logger.info("Shutting down (signal %d)…", signum)
        client.loop_stop()
        client.disconnect()
        _executor.shutdown(wait=False)
        sys.exit(0)

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)

    logger.info("Connecting to MQTT broker %s:%d …", MQTT_HOST, MQTT_PORT)
    client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)

    if GEMINI_KEEPALIVE_ENABLED:
        threading.Thread(target=_keepalive_loop, daemon=True, name="keepalive").start()
        logger.info("Keepalive ping is ENABLED.")
    else:
        logger.info("Keepalive ping is DISABLED (GEMINI_KEEPALIVE_ENABLED=false).")

    client.loop_forever()


if __name__ == "__main__":
    main()

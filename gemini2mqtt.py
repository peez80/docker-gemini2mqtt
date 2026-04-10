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
GEMINI_MODEL = get_env("GEMINI_MODEL")
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

def _read_stream_live(stream, is_stderr: bool, output_list: list, prefix: str) -> None:
    """Read a stream line by line, appending to the list and logging immediately."""
    for line in stream:
        output_list.append(line)
        line_clean = line.strip()
        if line_clean:
            if is_stderr:
                logger.warning("%sGemini CLI [stderr]: %s", prefix, line_clean)
            else:
                logger.info("%sGemini CLI [stdout]: %s", prefix, line_clean)


def _on_retry_exhausted(retry_state) -> str:
    """Called by tenacity when all attempts are exhausted; returns the last error string."""
    last_result = retry_state.outcome.result()
    log_context = retry_state.kwargs.get("log_context", "")
    prefix = f"[Topic: {log_context}] " if log_context else ""
    logger.error(
        "%sGemini call failed on all %d attempts. Last error: %s",
        prefix, GEMINI_RETRY_COUNT, last_result,
    )
    return last_result


def _before_sleep_custom_log(retry_state) -> None:
    """Custom logging during Tenacity retries to inject the contextual prefix."""
    log_context = retry_state.kwargs.get("log_context", "")
    prefix = f"[Topic: {log_context}] " if log_context else ""
    error_result = retry_state.outcome.result()
    
    logger.warning(
        "%sRetrying %s in %s seconds as it returned: %s",
        prefix,
        retry_state.fn.__name__,
        retry_state.next_action.sleep,
        error_result,
    )


@retry(
    stop=stop_after_attempt(GEMINI_RETRY_COUNT),
    wait=wait_fixed(5),
    retry=retry_if_result(lambda r: r.startswith("ERROR:")),
    before_sleep=_before_sleep_custom_log,
    retry_error_callback=_on_retry_exhausted,
)
def call_gemini(prompt: str, *, log_context: str = "") -> str:
    """Invoke the Gemini CLI and return the text response (with automatic retry)."""
    prefix = f"[Topic: {log_context}] " if log_context else ""
    cmd = build_standard_command(prompt)

    logger.debug("%sRunning command: %s", prefix, cmd)
    try:
        with subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        ) as process:

            stdout_lines: list = []
            stderr_lines: list = []

            t_out = threading.Thread(
                target=_read_stream_live,
                args=(process.stdout, False, stdout_lines, prefix),
                daemon=True,
                name="gemini-stdout-reader"
            )
            t_err = threading.Thread(
                target=_read_stream_live,
                args=(process.stderr, True, stderr_lines, prefix),
                daemon=True,
                name="gemini-stderr-reader"
            )

            t_out.start()
            t_err.start()

            # Pass the prompt to the CLI
            if prompt and process.stdin:
                process.stdin.write(prompt)
                process.stdin.close()  # VERY IMPORTANT to avoid deadlocks

            try:
                # Wait for the process to finish on its own within the timeout
                returncode = process.wait(timeout=GEMINI_TIMEOUT_SECONDS)
            except subprocess.TimeoutExpired:
                # Kill the hung process. This will close files and cause EOF in threads.
                logger.warning("%sTimeout reached (%d s). Killing process...", prefix, GEMINI_TIMEOUT_SECONDS)
                process.kill()
                # Wait briefly for process to actually terminate
                process.wait()

                # Cleanly wait for threads to exit (they will get EOF)
                t_out.join(timeout=1.0)
                t_err.join(timeout=1.0)

                stdout_so_far = "".join(stdout_lines).strip()
                stderr_so_far = "".join(stderr_lines).strip()

                logger.error(
                    "%sGemini CLI timed out after %d s.\n  stdout so far: %s\n  stderr so far: %s",
                    prefix,
                    GEMINI_TIMEOUT_SECONDS,
                    stdout_so_far if stdout_so_far else "<empty>",
                    stderr_so_far if stderr_so_far else "<empty>",
                )
                return "ERROR: Gemini CLI timed out."

            # Process finished normally
            t_out.join()
            t_err.join()

            stdout_output = "".join(stdout_lines).strip()
            stderr_output = "".join(stderr_lines).strip()

            if returncode != 0:
                logger.error("%sGemini CLI error (rc=%d): %s", prefix, returncode, stderr_output)
                return f"ERROR: Gemini CLI returned code {returncode}: {stderr_output}"

            if not stdout_output:
                error_msg = stderr_output if stderr_output else "Gemini CLI returned an empty response."
                logger.error("%sGemini CLI returned empty stdout. stderr: %s", prefix, error_msg)
                return f"ERROR: {error_msg}"

            return stdout_output

    except FileNotFoundError as exc:
        logger.error("%sGemini CLI not found: %s", prefix, exc)
        return f"ERROR: Gemini CLI not found: {exc}"
    except Exception as exc:  # pylint: disable=broad-except
        logger.exception("%sUnexpected error calling Gemini CLI", prefix)
        return f"ERROR: {exc}"


def build_standard_command(prompt: str) -> list[str]:
    """Build command for the standard Gemini API."""
    cmd = [GEMINI_CLI_PATH]
    if GEMINI_MODEL:
        cmd.extend(["--model", GEMINI_MODEL])
    cmd.extend(["-p", prompt])
    return cmd


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
        response = call_gemini(prompt, log_context=response_topic)
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
        response = call_gemini("ping", log_context="keepalive")
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

import os
import time
import threading
import logging
import subprocess
from typing import Optional
from google import genai
from google.genai import types
from tenacity import retry, retry_if_exception_type, retry_if_not_exception_type, stop_after_attempt, wait_exponential

from config import AppConfig

logger = logging.getLogger(__name__)

def _on_retry_exhausted(retry_state) -> str:
    """Called by tenacity when all attempts are exhausted; returns the last error string."""
    last_exc = retry_state.outcome.exception()
    log_context = retry_state.kwargs.get("log_context", "")
    prefix = f"[Topic: {log_context}] " if log_context else ""
    config = retry_state.kwargs.get("config")
    retry_count = config.gemini_retry_count if config else 3
    backend_name = config.ai_backend.capitalize() if config else "AI"
    logger.error(
        "%s%s call failed on all %d attempts. Last error: %s",
        prefix, backend_name, retry_count, last_exc,
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

@retry(
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(Exception),
    before_sleep=_before_sleep_custom_log,
    retry_error_callback=_on_retry_exhausted,
)
def _call_gemini_with_retry(prompt: str, config: AppConfig, client: genai.Client, log_context: str = "", files: list[str] = None, retry_state=None) -> str:
    """Invoke the Gemini API and return the text response (with automatic retry)."""
    prefix = f"[Topic: {log_context}] " if log_context else ""
    
    if retry_state and retry_state.attempt_number > config.gemini_retry_count:
        raise Exception(f"Max retries ({config.gemini_retry_count}) exceeded")

    logger.debug("%sCalling %s AI API (model: %s)...", prefix, config.ai_backend.capitalize(), config.gemini_model)
    
    contents = []
    uploaded_files = []
    
    try:
        import mimetypes
        for file_path in (files or []):
            if not os.path.exists(file_path):
                logger.warning("%sFile not found locally: %s", prefix, file_path)
                continue
            
            if config.ai_backend == "vertex":
                logger.debug("%sReading file inline for Vertex AI: %s", prefix, file_path)
                mime_type, _ = mimetypes.guess_type(file_path)
                if not mime_type:
                    mime_type = "application/octet-stream"
                with open(file_path, "rb") as fh:
                    contents.append(types.Part.from_bytes(data=fh.read(), mime_type=mime_type))
            else:
                logger.debug("%sUploading file to AI API: %s", prefix, file_path)
                file_ref = client.files.upload(file=file_path)
                uploaded_files.append(file_ref)
                contents.append(file_ref)

        
        contents.append(prompt)
        
        response = client.models.generate_content(
            model=config.gemini_model,
            contents=contents,
        )
        return response.text
    finally:
        for f_ref in uploaded_files:
            try:
                client.files.delete(name=f_ref.name)
                logger.debug("%sDeleted file from AI API: %s", prefix, f_ref.name)
            except Exception as e:
                logger.warning("%sFailed to delete file %s from AI API: %s", prefix, f_ref.name, e)

class AntigravityAuthError(Exception):
    """Raised when agy CLI fails due to missing, expired, or invalid OAuth credentials."""
    pass


@retry(
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_not_exception_type(AntigravityAuthError),
    before_sleep=_before_sleep_custom_log,
    retry_error_callback=_on_retry_exhausted,
)
def _call_agy_with_retry(prompt: str, config: AppConfig, log_context: str = "", files: list[str] = None, retry_state=None) -> str:
    """Invoke the agy CLI via subprocess and return the response (with automatic retry)."""
    prefix = f"[Topic: {log_context}] " if log_context else ""

    if retry_state and retry_state.attempt_number > config.gemini_retry_count:
        raise Exception(f"Max retries ({config.gemini_retry_count}) exceeded")

    full_prompt = prompt
    if files:
        full_prompt = f"{prompt}\n\n[Attached Files]\n" + "\n".join(f"- {f}" for f in files)

    cmd = [config.agy_binary_path, "-p", full_prompt]
    if config.agy_model:
        cmd.extend(["--model", config.agy_model])
    if config.agy_effort:
        cmd.extend(["--effort", config.agy_effort])
    if config.agy_dangerously_skip_permissions:
        cmd.append("--dangerously-skip-permissions")

    logger.debug("%sExecuting agy CLI command: %s", prefix, " ".join(cmd[:3]))

    try:
        res = subprocess.run(
            cmd,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=config.agy_timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as e:
        logger.error("%sagy CLI timed out after %d seconds", prefix, config.agy_timeout_seconds)
        raise RuntimeError(f"agy CLI timed out after {config.agy_timeout_seconds}s") from e

    if res.returncode != 0:
        stdout_low = res.stdout.lower()
        stderr_low = res.stderr.lower()
        if (
            "authentication required" in stdout_low
            or "authentication required" in stderr_low
            or "accounts.google.com/o/oauth2/auth" in stdout_low
            or "paste the authorization code" in stdout_low
        ):
            logger.error("%sAntigravity CLI authentication required: OAuth token is missing, expired, or invalid.", prefix)
            raise AntigravityAuthError("Antigravity CLI authentication required: OAuth token is missing, expired, or invalid.")

        err_msg = res.stderr.strip() or res.stdout.strip() or f"exit code {res.returncode}"
        logger.warning("%sagy CLI returned code %d: %s", prefix, res.returncode, err_msg)
        raise RuntimeError(f"agy CLI failed (code {res.returncode}): {err_msg}")

    return res.stdout.strip()

class AIClient:
    def __init__(self, config: AppConfig):
        self.config = config
        self.client: Optional[genai.Client] = None
        self._agy_start_lock = threading.Lock()
        self._last_agy_call_start: float = 0.0

        if config.ai_backend == "vertex":
            logger.info("Initializing Vertex AI client (project: %s, location: %s)", config.vertex_project, config.vertex_location)
            self.client = genai.Client(
                vertexai=True,
                project=config.vertex_project,
                location=config.vertex_location,
                http_options=types.HttpOptions(timeout=config.gemini_timeout_seconds * 1000)
            )
        elif config.ai_backend == "gemini":
            logger.info("Initializing Google AI client")
            self.client = genai.Client(
                http_options=types.HttpOptions(timeout=config.gemini_timeout_seconds * 1000)
            )
        elif config.ai_backend == "agy":
            logger.info("Initializing Antigravity (agy) CLI client (binary: %s)", config.agy_binary_path)

    def generate_content(self, prompt: str, files: list[str] = None, log_context: str = "") -> str:
        try:
            if self.config.ai_backend == "agy":
                with self._agy_start_lock:
                    now = time.monotonic()
                    elapsed = now - self._last_agy_call_start
                    delay = self.config.agy_concurrent_request_delay_seconds - elapsed
                    if self._last_agy_call_start > 0 and delay > 0:
                        prefix = f"[Topic: {log_context}] " if log_context else ""
                        logger.info(
                            "%sStaggering agy CLI start: waiting %.2fs to prevent token race condition...",
                            prefix, delay
                        )
                        time.sleep(delay)
                    self._last_agy_call_start = time.monotonic()

                return _call_agy_with_retry.retry_with(
                    stop=stop_after_attempt(self.config.gemini_retry_count)
                )(prompt=prompt, config=self.config, log_context=log_context, files=files)
            
            return _call_gemini_with_retry.retry_with(
                stop=stop_after_attempt(self.config.gemini_retry_count)
            )(prompt=prompt, config=self.config, client=self.client, log_context=log_context, files=files)
        except AntigravityAuthError as e:
            return f"ERROR: {e}"


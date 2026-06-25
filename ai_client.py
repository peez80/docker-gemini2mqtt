import os
import logging
from google import genai
from google.genai import types
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from config import AppConfig

logger = logging.getLogger(__name__)

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
        if files:
            for f in files:
                if not os.path.exists(f):
                    logger.warning("%sFile not found locally: %s", prefix, f)
                    continue
                
                if config.ai_backend == "vertex":
                    logger.debug("%sReading file inline for Vertex AI: %s", prefix, f)
                    mime_type, _ = mimetypes.guess_type(f)
                    if not mime_type:
                        mime_type = "application/octet-stream"
                    with open(f, "rb") as fh:
                        contents.append(types.Part.from_bytes(data=fh.read(), mime_type=mime_type))
                else:
                    logger.debug("%sUploading file to AI API: %s", prefix, f)
                    file_ref = client.files.upload(file=f)
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

class AIClient:
    def __init__(self, config: AppConfig):
        self.config = config
        if config.ai_backend == "vertex":
            logger.info("Initializing Vertex AI client (project: %s, location: %s)", config.vertex_project, config.vertex_location)
            self.client = genai.Client(
                vertexai=True,
                project=config.vertex_project,
                location=config.vertex_location,
                http_options=types.HttpOptions(timeout=config.gemini_timeout_seconds * 1000)
            )
        else:
            logger.info("Initializing Google AI client")
            self.client = genai.Client(
                http_options=types.HttpOptions(timeout=config.gemini_timeout_seconds * 1000)
            )

    def generate_content(self, prompt: str, files: list[str] = None, log_context: str = "") -> str:
        return _call_gemini_with_retry.retry_with(
            stop=stop_after_attempt(self.config.gemini_retry_count)
        )(prompt=prompt, config=self.config, client=self.client, log_context=log_context, files=files)

import subprocess
import pytest
from unittest.mock import MagicMock
from ai_client import AIClient
from config import AppConfig

def test_ai_client_generate_content(mocker):
    config = AppConfig(
        mqtt_host="localhost",
        mqtt_port=1883,
        mqtt_username=None,
        mqtt_password=None,
        mqtt_prompt_topic="test/prompt",
        gemini_model="gemini",
        gemini_max_concurrent=2,
        gemini_timeout_seconds=120,
        gemini_retry_count=1,
        ai_backend="gemini",
        vertex_project=None,
        vertex_location=None
    )
    
    # Mock the Client
    mock_client_class = mocker.patch("ai_client.genai.Client")
    mock_client_instance = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "Hello from AI"
    mock_client_instance.models.generate_content.return_value = mock_response
    mock_client_class.return_value = mock_client_instance
    
    ai_client = AIClient(config)
    response = ai_client.generate_content("Say hello", [], "test_context")
    
    assert response == "Hello from AI"
    mock_client_instance.models.generate_content.assert_called_once()
    
def test_ai_client_generate_content_with_files(mocker, tmp_path):
    config = AppConfig(
        mqtt_host="localhost",
        mqtt_port=1883,
        mqtt_username=None,
        mqtt_password=None,
        mqtt_prompt_topic="test/prompt",
        gemini_model="gemini",
        gemini_max_concurrent=2,
        gemini_timeout_seconds=120,
        gemini_retry_count=1,
        ai_backend="gemini",
        vertex_project=None,
        vertex_location=None
    )
    
    test_file = tmp_path / "test.txt"
    test_file.write_text("Hello")
    
    mock_client_class = mocker.patch("ai_client.genai.Client")
    mock_client_instance = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "Hello from AI"
    mock_client_instance.models.generate_content.return_value = mock_response
    
    mock_file_ref = MagicMock()
    mock_file_ref.name = "mock_name"
    mock_client_instance.files.upload.return_value = mock_file_ref
    
    mock_client_class.return_value = mock_client_instance
    
    ai_client = AIClient(config)
    response = ai_client.generate_content("Say hello", [str(test_file)], "test_context")
    
    assert response == "Hello from AI"
    mock_client_instance.files.upload.assert_called_once_with(file=str(test_file))
    mock_client_instance.files.delete.assert_called_once_with(name="mock_name")

def test_ai_client_vertex_init(mocker):
    config = AppConfig(
        mqtt_host="localhost",
        mqtt_port=1883,
        mqtt_username=None,
        mqtt_password=None,
        mqtt_prompt_topic="test/prompt",
        gemini_model="gemini",
        gemini_max_concurrent=2,
        gemini_timeout_seconds=120,
        gemini_retry_count=1,
        ai_backend="vertex",
        vertex_project="my-project",
        vertex_location="europe-west3"
    )
    
    mock_client_class = mocker.patch("ai_client.genai.Client")
    AIClient(config)
    
    # check if genai.Client was instantiated correctly
    mock_client_class.assert_called_once()
    kwargs = mock_client_class.call_args.kwargs
    assert kwargs.get("vertexai") is True
    assert kwargs.get("project") == "my-project"
    assert kwargs.get("location") == "europe-west3"

def test_ai_client_agy_generate_content(mocker):
    config = AppConfig(
        mqtt_host="localhost",
        mqtt_port=1883,
        mqtt_username=None,
        mqtt_password=None,
        mqtt_prompt_topic="test/prompt",
        gemini_model="gemini",
        gemini_max_concurrent=2,
        gemini_timeout_seconds=120,
        gemini_retry_count=1,
        ai_backend="agy",
        vertex_project=None,
        vertex_location=None,
        agy_binary_path="agy",
        agy_model=None,
        agy_effort=None,
        agy_timeout_seconds=120,
        agy_dangerously_skip_permissions=True,
    )

    mock_run = mocker.patch("subprocess.run")
    mock_run.return_value = MagicMock(returncode=0, stdout="Hello from agy\n", stderr="")

    mock_genai_class = mocker.patch("ai_client.genai.Client")

    ai_client = AIClient(config)
    assert ai_client.client is None
    mock_genai_class.assert_not_called()

    response = ai_client.generate_content("Say hello", [], "test_topic")

    assert response == "Hello from agy"
    mock_run.assert_called_once_with(
        ["agy", "-p", "Say hello", "--dangerously-skip-permissions"],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )

def test_ai_client_agy_generate_content_with_files(mocker):
    config = AppConfig(
        mqtt_host="localhost",
        mqtt_port=1883,
        mqtt_username=None,
        mqtt_password=None,
        mqtt_prompt_topic="test/prompt",
        gemini_model="gemini",
        gemini_max_concurrent=2,
        gemini_timeout_seconds=120,
        gemini_retry_count=1,
        ai_backend="agy",
        vertex_project=None,
        vertex_location=None,
        agy_binary_path="agy",
        agy_model=None,
        agy_effort=None,
        agy_timeout_seconds=120,
        agy_dangerously_skip_permissions=True,
    )

    mock_run = mocker.patch("subprocess.run")
    mock_run.return_value = MagicMock(returncode=0, stdout="File analyzed\n", stderr="")

    ai_client = AIClient(config)
    response = ai_client.generate_content("Analyze", ["/path/to/file1.txt", "/path/to/file2.txt"], "test_topic")

    assert response == "File analyzed"
    expected_prompt = "Analyze\n\n[Attached Files]\n- /path/to/file1.txt\n- /path/to/file2.txt"
    mock_run.assert_called_once_with(
        ["agy", "-p", expected_prompt, "--dangerously-skip-permissions"],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )

def test_ai_client_agy_with_model_and_effort(mocker):
    config = AppConfig(
        mqtt_host="localhost",
        mqtt_port=1883,
        mqtt_username=None,
        mqtt_password=None,
        mqtt_prompt_topic="test/prompt",
        gemini_model="gemini",
        gemini_max_concurrent=2,
        gemini_timeout_seconds=120,
        gemini_retry_count=1,
        ai_backend="agy",
        vertex_project=None,
        vertex_location=None,
        agy_binary_path="/custom/bin/agy",
        agy_model="gemini-3.6-flash-high",
        agy_effort="high",
        agy_timeout_seconds=45,
        agy_dangerously_skip_permissions=False,
    )

    mock_run = mocker.patch("subprocess.run")
    mock_run.return_value = MagicMock(returncode=0, stdout="Custom model response", stderr="")

    ai_client = AIClient(config)
    response = ai_client.generate_content("Say hello", [], "test_topic")

    assert response == "Custom model response"
    mock_run.assert_called_once_with(
        ["/custom/bin/agy", "-p", "Say hello", "--model", "gemini-3.6-flash-high", "--effort", "high"],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=45,
        check=False,
    )

def test_ai_client_agy_failure_and_retry(mocker):
    config = AppConfig(
        mqtt_host="localhost",
        mqtt_port=1883,
        mqtt_username=None,
        mqtt_password=None,
        mqtt_prompt_topic="test/prompt",
        gemini_model="gemini",
        gemini_max_concurrent=2,
        gemini_timeout_seconds=120,
        gemini_retry_count=2,
        ai_backend="agy",
        vertex_project=None,
        vertex_location=None,
        agy_binary_path="agy",
        agy_model=None,
        agy_effort=None,
        agy_timeout_seconds=120,
        agy_dangerously_skip_permissions=True,
    )

    mock_run = mocker.patch("subprocess.run")
    mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="Model quota exceeded")

    ai_client = AIClient(config)
    response = ai_client.generate_content("Say hello", [], "test_topic")

    assert "ERROR: agy CLI failed (code 1): Model quota exceeded" in response
    assert mock_run.call_count == 2


def test_ai_client_agy_auth_failure_fail_fast(mocker):
    """Test that authentication failure in agy CLI fails fast without retries."""
    config = AppConfig(
        mqtt_host="localhost",
        mqtt_port=1883,
        mqtt_username=None,
        mqtt_password=None,
        mqtt_prompt_topic="test/prompt",
        gemini_model="gemini-2.5-flash",
        gemini_max_concurrent=2,
        gemini_timeout_seconds=30,
        gemini_retry_count=3,
        ai_backend="agy",
        vertex_project=None,
        vertex_location=None,
        agy_binary_path="agy",
        agy_model=None,
        agy_effort=None,
        agy_timeout_seconds=120,
        agy_dangerously_skip_permissions=True,
    )

    mock_run = mocker.patch("subprocess.run")
    mock_run.return_value = MagicMock(
        returncode=1,
        stdout="Authentication required. Please visit the URL to log in: https://accounts.google.com/o/oauth2/auth",
        stderr=""
    )

    ai_client = AIClient(config)
    response = ai_client.generate_content("Say hello", [], "test_topic")

    assert "authentication required" in response.lower() or "authentication failed" in response.lower()
    # Must fail fast without retrying 3 times
    assert mock_run.call_count == 1




def test_has_agy_auth_helper(monkeypatch, tmp_path):
    from tests.test_e2e import _has_agy_auth


    # Case 1: No file, no env var
    fake_home = tmp_path / "home_empty"
    fake_home.mkdir()
    monkeypatch.setenv("HOME", str(fake_home))
    monkeypatch.delenv("ANTIGRAVITY_OAUTH_TOKEN", raising=False)
    assert not _has_agy_auth()

    # Case 2: Env var provided with valid token
    monkeypatch.setenv("ANTIGRAVITY_OAUTH_TOKEN", "secret-token-123")
    assert _has_agy_auth()

    # Case 3: Env var is empty or only whitespace
    monkeypatch.setenv("ANTIGRAVITY_OAUTH_TOKEN", "")
    assert not _has_agy_auth()
    monkeypatch.setenv("ANTIGRAVITY_OAUTH_TOKEN", "   \n\t  ")
    assert not _has_agy_auth()

    # Case 4: Token file with whitespace/newline only (e.g. echo "$EMPTY_SECRET" > file)
    monkeypatch.delenv("ANTIGRAVITY_OAUTH_TOKEN", raising=False)
    token_dir = fake_home / ".gemini" / "antigravity-cli"
    token_dir.mkdir(parents=True, exist_ok=True)
    token_file = token_dir / "antigravity-oauth-token"
    
    token_file.write_text("\n")
    assert not _has_agy_auth()

    token_file.write_text("   \n   ")
    assert not _has_agy_auth()

    # Case 5: Token file with invalid JSON or empty token inside JSON
    token_file.write_text('{"token": ""}')
    assert not _has_agy_auth()

    # Case 6: Token file with valid JSON token
    token_file.write_text('{"token": "valid-token-xyz", "auth_method": "oauth"}')
    assert _has_agy_auth()

    # Case 7: Token file with valid non-JSON string
    token_file.write_text("valid-raw-oauth-token")
    assert _has_agy_auth()

    # Case 8: Nested token dict with refresh_token
    token_file.write_text('{"token": {"refresh_token": "1//refresh-token-xyz", "token_type": "Bearer"}, "auth_method": "oauth"}')
    assert _has_agy_auth()

    # Case 9: Nested token dict with access_token and expiry
    token_file.write_text('{"token": {"access_token": "ya29.access-xyz", "expiry": "2026-12-31T00:00:00Z"}, "auth_method": "oauth"}')
    assert _has_agy_auth()


def test_has_mounted_agy_config_helper(monkeypatch, tmp_path):
    from tests.test_e2e import _has_mounted_agy_config

    fake_home = tmp_path / "home_mounted"
    fake_home.mkdir()
    monkeypatch.setenv("HOME", str(fake_home))

    # Initially missing
    assert not _has_mounted_agy_config()

    # Empty token file
    token_dir = fake_home / ".gemini" / "antigravity-cli"
    token_dir.mkdir(parents=True)
    token_file = token_dir / "antigravity-oauth-token"
    token_file.write_text("   \n")
    assert not _has_mounted_agy_config()

    # Valid token file with nested refresh_token
    token_file.write_text('{"token": {"refresh_token": "1//refresh-123"}}')
    assert _has_mounted_agy_config()



def test_get_active_token_payload_helper(monkeypatch, tmp_path):
    from tests.test_e2e import _get_active_token_payload

    fake_home = tmp_path / "home_payload"
    fake_home.mkdir()
    monkeypatch.setenv("HOME", str(fake_home))

    # Env var precedence
    monkeypatch.setenv("ANTIGRAVITY_OAUTH_TOKEN", "env-token-123")
    assert _get_active_token_payload() == "env-token-123"

    # File fallback
    monkeypatch.delenv("ANTIGRAVITY_OAUTH_TOKEN", raising=False)
    token_dir = fake_home / ".gemini" / "antigravity-cli"
    token_dir.mkdir(parents=True)
    token_file = token_dir / "antigravity-oauth-token"
    token_file.write_text("file-token-456")
    assert _get_active_token_payload() == "file-token-456"


def test_ai_client_agy_staggered_start(mocker):
    import threading
    import time
    config = AppConfig(
        mqtt_host="localhost",
        mqtt_port=1883,
        mqtt_username=None,
        mqtt_password=None,
        mqtt_prompt_topic="test/prompt",
        gemini_model="gemini",
        gemini_max_concurrent=2,
        gemini_timeout_seconds=120,
        gemini_retry_count=1,
        ai_backend="agy",
        vertex_project=None,
        vertex_location=None,
        agy_concurrent_request_delay_seconds=0.2,
    )
    ai_client = AIClient(config)
    start_times = []
    lock = threading.Lock()

    def fake_run(*args, **kwargs):
        with lock:
            start_times.append(time.monotonic())
        time.sleep(0.05)
        return MagicMock(returncode=0, stdout="Result\n", stderr="")

    mocker.patch("subprocess.run", side_effect=fake_run)

    t1 = threading.Thread(target=ai_client.generate_content, args=("prompt 1",))
    t2 = threading.Thread(target=ai_client.generate_content, args=("prompt 2",))

    t1.start()
    t2.start()
    t1.join()
    t2.join()

    assert len(start_times) == 2
    delay_diff = start_times[1] - start_times[0]
    assert delay_diff >= 0.18, f"Expected at least ~0.2s delay between starts, got {delay_diff}s"


def test_ai_client_agy_parallel_execution(mocker):
    import threading
    import time
    config = AppConfig(
        mqtt_host="localhost",
        mqtt_port=1883,
        mqtt_username=None,
        mqtt_password=None,
        mqtt_prompt_topic="test/prompt",
        gemini_model="gemini",
        gemini_max_concurrent=2,
        gemini_timeout_seconds=120,
        gemini_retry_count=1,
        ai_backend="agy",
        vertex_project=None,
        vertex_location=None,
        agy_concurrent_request_delay_seconds=0.1,
    )
    ai_client = AIClient(config)
    active_calls = 0
    max_concurrent_seen = 0
    lock = threading.Lock()

    def fake_run(*args, **kwargs):
        nonlocal active_calls, max_concurrent_seen
        with lock:
            active_calls += 1
            if active_calls > max_concurrent_seen:
                max_concurrent_seen = active_calls
        time.sleep(0.3)
        with lock:
            active_calls -= 1
        return MagicMock(returncode=0, stdout="Result\n", stderr="")

    mocker.patch("subprocess.run", side_effect=fake_run)

    t1 = threading.Thread(target=ai_client.generate_content, args=("prompt 1",))
    t2 = threading.Thread(target=ai_client.generate_content, args=("prompt 2",))

    t1.start()
    t2.start()
    t1.join()
    t2.join()

    assert max_concurrent_seen == 2, f"Expected 2 concurrent calls during overlap, got {max_concurrent_seen}"


def test_ai_client_gemini_no_delay(mocker):
    import threading
    import time
    config = AppConfig(
        mqtt_host="localhost",
        mqtt_port=1883,
        mqtt_username=None,
        mqtt_password=None,
        mqtt_prompt_topic="test/prompt",
        gemini_model="gemini",
        gemini_max_concurrent=2,
        gemini_timeout_seconds=120,
        gemini_retry_count=1,
        ai_backend="gemini",
        vertex_project=None,
        vertex_location=None,
    )
    mock_client_class = mocker.patch("ai_client.genai.Client")
    mock_client_instance = MagicMock()
    mock_response = MagicMock(text="Gemini Answer")
    mock_client_class.return_value = mock_client_instance

    start_times = []
    lock = threading.Lock()

    def fake_gen(*args, **kwargs):
        with lock:
            start_times.append(time.monotonic())
        time.sleep(0.05)
        return mock_response

    mock_client_instance.models.generate_content.side_effect = fake_gen

    ai_client = AIClient(config)

    t1 = threading.Thread(target=ai_client.generate_content, args=("prompt 1",))
    t2 = threading.Thread(target=ai_client.generate_content, args=("prompt 2",))

    t1.start()
    t2.start()
    t1.join()
    t2.join()

    assert len(start_times) == 2
    delay_diff = abs(start_times[1] - start_times[0])
    assert delay_diff < 0.1, f"Expected Gemini calls to start without delay, got {delay_diff}s"


def test_ai_client_agy_five_concurrent_staggered_start(mocker, caplog):
    import threading
    import time
    import logging

    caplog.set_level(logging.INFO)

    config = AppConfig(
        mqtt_host="localhost",
        mqtt_port=1883,
        mqtt_username=None,
        mqtt_password=None,
        mqtt_prompt_topic="test/prompt",
        gemini_model="gemini",
        gemini_max_concurrent=5,
        gemini_timeout_seconds=120,
        gemini_retry_count=1,
        ai_backend="agy",
        vertex_project=None,
        vertex_location=None,
        agy_concurrent_request_delay_seconds=0.1,
    )
    ai_client = AIClient(config)
    start_times = []
    lock = threading.Lock()

    def fake_run(*args, **kwargs):
        with lock:
            start_times.append(time.monotonic())
        time.sleep(0.05)
        return MagicMock(returncode=0, stdout="Result\n", stderr="")

    mocker.patch("subprocess.run", side_effect=fake_run)

    threads = [
        threading.Thread(
            target=ai_client.generate_content,
            args=(f"prompt {i}",),
            kwargs={"log_context": f"topic_{i}"},
        )
        for i in range(5)
    ]

    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(start_times) == 5
    for i in range(1, len(start_times)):
        gap = start_times[i] - start_times[i - 1]
        assert gap >= 0.08, f"Expected at least ~0.1s between start {i-1} and {i}, got {gap}s"

    start_logs = [r.message for r in caplog.records if "Starting agy CLI execution" in r.message]
    assert len(start_logs) == 5








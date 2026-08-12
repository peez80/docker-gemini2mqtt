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


def test_has_agy_auth_helper(monkeypatch, tmp_path):
    from tests.test_e2e import _has_agy_auth

    # Case 1: No file, no env var
    fake_home = tmp_path / "home_empty"
    fake_home.mkdir()
    monkeypatch.setenv("HOME", str(fake_home))
    monkeypatch.delenv("ANTIGRAVITY_OAUTH_TOKEN", raising=False)
    assert not _has_agy_auth()

    # Case 2: Env var provided
    monkeypatch.setenv("ANTIGRAVITY_OAUTH_TOKEN", "secret-token-123")
    assert _has_agy_auth()

    # Case 3: Token file present
    monkeypatch.delenv("ANTIGRAVITY_OAUTH_TOKEN", raising=False)
    token_dir = fake_home / ".gemini" / "antigravity-cli"
    token_dir.mkdir(parents=True)
    token_file = token_dir / "antigravity-oauth-token"
    token_file.write_text("oauth-token-content")
    assert _has_agy_auth()



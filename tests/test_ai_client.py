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
        gemini_retry_count=1
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
        gemini_retry_count=1
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

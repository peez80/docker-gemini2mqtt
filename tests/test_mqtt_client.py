import pytest
from unittest.mock import MagicMock
from mqtt_client import MqttClient

def test_parse_message_valid_payload():
    # Will be tested through static or class method, or module level if we put it there.
    # Let's assume parse_message is a module level function in mqtt_client
    from mqtt_client import parse_message
    topic, prompt, files = parse_message("my/topic|Hello Gemini")
    assert topic == "my/topic"
    assert prompt == "Hello Gemini"
    assert files == []

def test_parse_message_invalid_payload():
    from mqtt_client import parse_message
    assert parse_message("invalid_payload_without_pipe") is None
    topic, prompt, files = parse_message("topic|with|multiple|pipes")
    assert topic == "topic"
    assert prompt == "with|multiple|pipes"
    assert files == []

def test_parse_message_json_payload():
    from mqtt_client import parse_message
    import json
    payload = json.dumps({"response_topic": "json/topic", "prompt": "Hello JSON"})
    topic, prompt, files = parse_message(payload)
    assert topic == "json/topic"
    assert prompt == "Hello JSON"
    assert files == []

    payload = json.dumps({"response_topic": "json/topic", "prompt": "Hello JSON", "files": ["/tmp/file.txt"]})
    topic, prompt, files = parse_message(payload)
    assert files == ["/tmp/file.txt"]

    payload = json.dumps({"response_topic": "json/topic"})
    assert parse_message(payload) is None

def test_mqtt_client_callbacks(monkeypatch):
    from config import AppConfig
    config = AppConfig(
        mqtt_host="localhost",
        mqtt_port=1883,
        mqtt_username=None,
        mqtt_password=None,
        mqtt_prompt_topic="test/prompt",
        gemini_model="gemini",
        gemini_max_concurrent=2,
        gemini_timeout_seconds=120,
        gemini_retry_count=3
    )
    
    # We will test that when on_message is called, it triggers our registered callback
    client = MqttClient(config)
    
    callback_mock = MagicMock()
    client.register_message_callback(callback_mock)
    
    # Simulate receiving a message
    msg = MagicMock()
    msg.topic = "test/prompt"
    msg.payload = b"response/topic|Hello from test"
    
    client.on_message(None, None, msg)
    
    callback_mock.assert_called_once_with("response/topic", "Hello from test", [])

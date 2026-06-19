import time
import pytest
from unittest.mock import MagicMock
import paho.mqtt.client as mqtt

from gemini2mqtt import parse_message, Gemini2MqttApp

def test_parse_message_valid_payload():
    topic, prompt = parse_message("my/topic|Hello Gemini")
    assert topic == "my/topic"
    assert prompt == "Hello Gemini"

def test_parse_message_invalid_payload():
    assert parse_message("invalid_payload_without_pipe") is None
    # A payload with multiple pipes is perfectly valid, the prompt simply contains a pipe.
    topic, prompt = parse_message("topic|with|multiple|pipes")
    assert topic == "topic"
    assert prompt == "with|multiple|pipes"

def test_full_message_flow(mqtt_broker, monkeypatch, mocker):
    host, port = mqtt_broker

    # Patch environment variables
    monkeypatch.setenv("MQTT_HOST", host)
    monkeypatch.setenv("MQTT_PORT", str(port))
    monkeypatch.setenv("MQTT_PROMPT_TOPIC", "test/prompt")
    monkeypatch.setenv("GEMINI_API_KEY", "dummy_key")

    # Mock the Google GenAI Client
    mock_client_instance = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "Mocked AI Response"
    mock_client_instance.models.generate_content.return_value = mock_response

    # Patch the genai.Client constructor to return our mock
    mocker.patch("gemini2mqtt.genai.Client", return_value=mock_client_instance)

    # Initialize AppConfig using environment variables
    from gemini2mqtt import load_config
    config = load_config()

    # Start the app
    app = Gemini2MqttApp(config)
    app.start(background=True)

    try:
        time.sleep(0.5)

        received_messages = []
        def on_test_message(client, userdata, msg):
            received_messages.append(msg.payload.decode("utf-8"))

        test_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        test_client.on_message = on_test_message
        test_client.connect(host, port)
        test_client.loop_start()

        response_topic = "test/response"
        test_client.subscribe(response_topic)
        time.sleep(0.5)

        # Publish a prompt to the app
        prompt_payload = f"{response_topic}|Hello AI"
        test_client.publish(config.mqtt_prompt_topic, prompt_payload)

        # Poll for the response
        start_time = time.time()
        while time.time() - start_time < 5:
            if received_messages:
                break
            time.sleep(0.1)

        # Verify the mock was called correctly
        mock_client_instance.models.generate_content.assert_called_once()
        
        # Verify the response message was published back via MQTT
        assert len(received_messages) == 1
        assert received_messages[0] == f"{response_topic}|Mocked AI Response"

    finally:
        test_client.loop_stop()
        test_client.disconnect()
        app.stop()


def test_api_failure_flow(mqtt_broker, monkeypatch, mocker):
    """Test that if Gemini API fails repeatedly, an ERROR message is published back."""
    host, port = mqtt_broker
    monkeypatch.setenv("MQTT_HOST", host)
    monkeypatch.setenv("MQTT_PORT", str(port))
    monkeypatch.setenv("MQTT_PROMPT_TOPIC", "test/prompt_fail")
    monkeypatch.setenv("GEMINI_API_KEY", "dummy_key")
    # Reduce retries for fast testing
    monkeypatch.setenv("GEMINI_RETRY_COUNT", "1")

    # Mock the API to always raise an Exception
    mock_client_instance = MagicMock()
    mock_client_instance.models.generate_content.side_effect = Exception("API completely down")
    mocker.patch("gemini2mqtt.genai.Client", return_value=mock_client_instance)

    from gemini2mqtt import load_config
    config = load_config()

    app = Gemini2MqttApp(config)
    app.start(background=True)

    try:
        time.sleep(0.5)
        received_messages = []
        def on_test_message(client, userdata, msg):
            received_messages.append(msg.payload.decode("utf-8"))

        test_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        test_client.on_message = on_test_message
        test_client.connect(host, port)
        test_client.loop_start()

        response_topic = "test/response_fail"
        test_client.subscribe(response_topic)
        time.sleep(0.5)

        test_client.publish(config.mqtt_prompt_topic, f"{response_topic}|Fail me")

        start_time = time.time()
        while time.time() - start_time < 5:
            if received_messages:
                break
            time.sleep(0.1)

        # Verify that an error string was returned over MQTT
        assert len(received_messages) == 1
        assert "ERROR: API completely down" in received_messages[0]

    finally:
        test_client.loop_stop()
        test_client.disconnect()
        app.stop()

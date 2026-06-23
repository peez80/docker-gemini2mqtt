import os
import time
import json
import pytest
import paho.mqtt.client as mqtt

from gemini2mqtt import load_config, Gemini2MqttApp

@pytest.mark.e2e
@pytest.mark.skipif(not os.environ.get("GEMINI_API_KEY"), reason="GEMINI_API_KEY not set in environment. Skipping E2E test.")
def test_real_gemini_api_integration(mqtt_broker, monkeypatch, tmp_path):
    """
    End-to-End integration test using JSON payload and a local file.
    """
    host, port = mqtt_broker
    
    monkeypatch.setenv("MQTT_HOST", host)
    monkeypatch.setenv("MQTT_PORT", str(port))
    monkeypatch.setenv("MQTT_PROMPT_TOPIC", "test/e2e_prompt_json")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-3.1-flash-lite")

    config = load_config()
    app = Gemini2MqttApp(config)
    
    app.start(background=True)

    try:
        time.sleep(0.5)

        received_messages = []
        def on_message(client, userdata, msg):
            received_messages.append(msg.payload.decode("utf-8"))

        test_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        test_client.on_message = on_message
        test_client.connect(host, port)
        test_client.loop_start()

        response_topic = "test/e2e_response_json"
        test_client.subscribe(response_topic)
        time.sleep(0.5)

        # Create a temporary file
        test_file = tmp_path / "secret.txt"
        test_file.write_text("The secret code is BANANA.")

        # Publish the JSON payload
        payload = {
            "response_topic": response_topic,
            "prompt": "Read the attached text document and output exactly the secret code word found inside it. Do not say anything else.",
            "files": [str(test_file)]
        }
        test_client.publish(config.mqtt_prompt_topic, json.dumps(payload))

        start_time = time.time()
        while time.time() - start_time < 60:
            if received_messages:
                break
            time.sleep(0.5)

        assert len(received_messages) > 0, "Timeout: No response received from real Gemini API"
        response_text = received_messages[0].upper()
        print(f'Received response: {response_text}')
        assert "BANANA" in response_text, f"Expected 'BANANA' in response, got: {received_messages[0]}"

    finally:
        test_client.loop_stop()
        test_client.disconnect()
        app.stop()

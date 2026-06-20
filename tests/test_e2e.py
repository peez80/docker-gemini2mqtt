import os
import time
import pytest
import paho.mqtt.client as mqtt

from gemini2mqtt import load_config, Gemini2MqttApp

@pytest.mark.e2e
@pytest.mark.skipif(not os.environ.get("GEMINI_API_KEY"), reason="GEMINI_API_KEY not set in environment. Skipping E2E test.")
def test_real_gemini_api(mqtt_broker, monkeypatch):
    """
    End-to-End test that connects to the real Google Gemini API.
    Requires GEMINI_API_KEY to be set in the environment or a .env file.
    """
    host, port = mqtt_broker
    
    # Configure the environment to use the testcontainer Mosquitto broker
    monkeypatch.setenv("MQTT_HOST", host)
    monkeypatch.setenv("MQTT_PORT", str(port))
    monkeypatch.setenv("MQTT_PROMPT_TOPIC", "test/e2e_prompt")
    
    # Force a fast model for the E2E test to save tokens and time
    monkeypatch.setenv("GEMINI_MODEL", "gemini-3.1-flash-lite")

    config = load_config()
    app = Gemini2MqttApp(config)
    
    # Start the app in the background (no mocking of genai.Client!)
    app.start(background=True)

    try:
        # Give the app a moment to connect to MQTT
        time.sleep(0.5)

        received_messages = []
        def on_message(client, userdata, msg):
            received_messages.append(msg.payload.decode("utf-8"))

        # Setup test MQTT client to send the prompt and receive the response
        test_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        test_client.on_message = on_message
        test_client.connect(host, port)
        test_client.loop_start()

        response_topic = "test/e2e_response"
        test_client.subscribe(response_topic)
        time.sleep(0.5)

        # Publish the prompt
        # We ask for a simple, deterministic string to verify
        prompt_payload = f"{response_topic}|Say exactly 'PONG' and nothing else."
        test_client.publish(config.mqtt_prompt_topic, prompt_payload)

        # Poll for the response. Real API calls can take a few seconds.
        # We allow up to 30 seconds timeout.
        start_time = time.time()
        while time.time() - start_time < 30:
            if received_messages:
                break
            time.sleep(0.5)

        # Verify we received a response and it contains 'PONG'
        assert len(received_messages) > 0, "Timeout: No response received from real Gemini API"
        response_text = received_messages[0].upper()
        print(f'Received response: {response_text}')
        assert "PONG" in response_text, f"Expected 'PONG' in response, got: {received_messages[0]}"

    finally:
        test_client.loop_stop()
        test_client.disconnect()
        app.stop()

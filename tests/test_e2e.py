import os
import time
import json
import shutil
import pytest
import paho.mqtt.client as mqtt

from config import load_config
from main import Gemini2MqttApp

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


@pytest.mark.e2e
@pytest.mark.skipif(
    os.environ.get("CI") == "true" or (not os.environ.get("VERTEX_GOOGLE_CLOUD_PROJECT") and not os.path.exists(".vertex_test_key.json")),
    reason="Vertex AI project or credentials not set in environment. Skipping Vertex E2E test."
)
def test_real_vertex_api_integration(mqtt_broker, monkeypatch, tmp_path):
    """
    End-to-End integration test for Vertex AI using JSON payload and a local file.
    """
    host, port = mqtt_broker
    
    monkeypatch.setenv("MQTT_HOST", host)
    monkeypatch.setenv("MQTT_PORT", str(port))
    monkeypatch.setenv("MQTT_PROMPT_TOPIC", "test/e2e_prompt_vertex")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-3.1-flash-lite")
    monkeypatch.setenv("AI_BACKEND", "vertex")
    
    vertex_project = os.environ.get("VERTEX_GOOGLE_CLOUD_PROJECT", "")
    
    if not os.environ.get("GOOGLE_APPLICATION_CREDENTIALS") and os.path.exists(".vertex_test_key.json"):
        monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", os.path.abspath(".vertex_test_key.json"))
        if not vertex_project:
            try:
                with open(".vertex_test_key.json") as f:
                    key_data = json.load(f)
                    vertex_project = key_data.get("project_id", "")
            except Exception:
                pass
                
    monkeypatch.setenv("VERTEX_GOOGLE_CLOUD_PROJECT", vertex_project)

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

        response_topic = "test/e2e_response_vertex"
        test_client.subscribe(response_topic)
        time.sleep(0.5)

        test_file = tmp_path / "secret_vertex.txt"
        test_file.write_text("The secret code is ORANGE.")

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

        assert len(received_messages) > 0, "Timeout: No response received from real Vertex AI API"
        response_text = received_messages[0].upper()
        print(f'Received response: {response_text}')
        assert "ORANGE" in response_text, f"Expected 'ORANGE' in response, got: {received_messages[0]}"

    finally:
        test_client.loop_stop()
        test_client.disconnect()
        app.stop()


def _is_valid_token_dict(data: dict) -> bool:
    if not isinstance(data, dict):
        return False
    token_obj = data.get("token")
    if isinstance(token_obj, dict):
        return bool(token_obj.get("access_token") or token_obj.get("refresh_token") or token_obj.get("token"))
    if token_obj and str(token_obj).strip():
        return True
    return bool(data.get("access_token") or data.get("refresh_token") or data.get("id_token"))


def _has_agy_auth() -> bool:
    """Check if a valid Antigravity CLI OAuth token, refresh token, or environment secret is available."""
    # 1. Check environment variable
    env_token = os.environ.get("ANTIGRAVITY_OAUTH_TOKEN", "").strip()
    if env_token:
        try:
            data = json.loads(env_token)
            if isinstance(data, dict):
                return _is_valid_token_dict(data)
            elif str(data).strip():
                return True
        except Exception:
            if len(env_token) > 0:
                return True

    # 2. Check token file
    token_path = os.path.expanduser("~/.gemini/antigravity-cli/antigravity-oauth-token")
    if os.path.exists(token_path) and os.path.isfile(token_path):
        try:
            with open(token_path, "r", encoding="utf-8") as f:
                content = f.read().strip()
            if not content:
                return False
            try:
                data = json.loads(content)
                if isinstance(data, dict):
                    return _is_valid_token_dict(data)
                return bool(str(data).strip())
            except Exception:
                return len(content) > 0
        except Exception:
            return False

    return False


def _has_mounted_agy_config() -> bool:
    """Check if a mounted/existing ~/.gemini/antigravity-cli token file is available and valid."""
    token_path = os.path.expanduser("~/.gemini/antigravity-cli/antigravity-oauth-token")
    if os.path.exists(token_path) and os.path.isfile(token_path):
        try:
            with open(token_path, "r", encoding="utf-8") as f:
                content = f.read().strip()
            if not content:
                return False
            try:
                data = json.loads(content)
                if isinstance(data, dict):
                    return _is_valid_token_dict(data)
                return bool(str(data).strip())
            except Exception:
                return len(content) > 0
        except Exception:
            return False
    return False



def _get_active_token_payload() -> str:
    """Get the active OAuth token payload from env var or local config file."""
    env_token = os.environ.get("ANTIGRAVITY_OAUTH_TOKEN", "").strip()
    if env_token:
        return env_token
    token_path = os.path.expanduser("~/.gemini/antigravity-cli/antigravity-oauth-token")
    if os.path.exists(token_path) and os.path.isfile(token_path):
        try:
            with open(token_path, "r", encoding="utf-8") as f:
                return f.read().strip()
        except Exception:
            pass
    return ""


@pytest.mark.e2e
@pytest.mark.skipif(
    not shutil.which("agy") and not os.path.exists("/usr/local/bin/agy") and not os.environ.get("AGY_BINARY_PATH"),
    reason="agy CLI not available in environment. Skipping agy E2E test."
)
@pytest.mark.skipif(
    not _has_mounted_agy_config(),
    reason="Mounted agy config directory (~/.gemini/antigravity-cli) not found. Skipping mounted config test."
)
def test_real_agy_cli_integration_mounted_config(mqtt_broker, monkeypatch, tmp_path):
    """
    End-to-End integration test using agy CLI with pre-mounted ~/.gemini directory.
    """
    # Ensure allowNonWorkspaceAccess is enabled for headless test execution
    settings_file = os.path.expanduser("~/.gemini/antigravity-cli/settings.json")
    if not os.path.exists(settings_file):
        os.makedirs(os.path.dirname(settings_file), exist_ok=True)
        with open(settings_file, "w") as f:
            f.write(json.dumps({"allowNonWorkspaceAccess": True}))

    host, port = mqtt_broker

    monkeypatch.setenv("MQTT_HOST", host)
    monkeypatch.setenv("MQTT_PORT", str(port))
    monkeypatch.setenv("MQTT_PROMPT_TOPIC", "test/e2e_prompt_agy_mounted")
    monkeypatch.setenv("AI_BACKEND", "agy")
    monkeypatch.setenv("AGY_TIMEOUT_SECONDS", "120")
    monkeypatch.setenv("AGY_DANGEROUSLY_SKIP_PERMISSIONS", "true")

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

        response_topic = "test/e2e_response_agy_mounted"
        test_client.subscribe(response_topic)
        time.sleep(0.5)

        test_file = tmp_path / "secret_agy_mounted.txt"
        test_file.write_text("The secret code is DRAGONFRUIT.")

        payload = {
            "response_topic": response_topic,
            "prompt": "Read the attached text document and output exactly the secret code word found inside it. Do not say anything else.",
            "files": [str(test_file)]
        }
        test_client.publish(config.mqtt_prompt_topic, json.dumps(payload))

        start_time = time.time()
        while time.time() - start_time < 120:
            if received_messages:
                break
            time.sleep(0.5)

        assert len(received_messages) > 0, "Timeout: No response received from real agy CLI"
        response_text = received_messages[0].upper()
        print(f'Received response: {response_text}')
        assert "DRAGONFRUIT" in response_text, f"Expected 'DRAGONFRUIT' in response, got: {received_messages[0]}"

    finally:
        test_client.loop_stop()
        test_client.disconnect()
        app.stop()


@pytest.mark.e2e
@pytest.mark.skipif(
    not shutil.which("agy") and not os.path.exists("/usr/local/bin/agy") and not os.environ.get("AGY_BINARY_PATH"),
    reason="agy CLI not available in environment. Skipping agy E2E test."
)
@pytest.mark.skipif(
    not _has_agy_auth(),
    reason="No valid ANTIGRAVITY_OAUTH_TOKEN available. Skipping isolated OAuth token test."
)
def test_real_agy_cli_integration_env_token_isolated(mqtt_broker, monkeypatch, tmp_path):
    """
    End-to-End integration test using agy CLI in an isolated sandbox environment
    bootstrapped strictly via the ANTIGRAVITY_OAUTH_TOKEN environment variable.
    """
    token_payload = _get_active_token_payload()
    assert token_payload, "Token payload must be non-empty"

    # Set up isolated home directory
    isolated_home = tmp_path / "isolated_home"
    isolated_gemini_dir = isolated_home / ".gemini" / "antigravity-cli"
    isolated_gemini_dir.mkdir(parents=True, exist_ok=True)

    isolated_token_file = isolated_gemini_dir / "antigravity-oauth-token"
    isolated_token_file.write_text(token_payload)
    os.chmod(isolated_token_file, 0o600)

    isolated_settings = isolated_gemini_dir / "settings.json"
    isolated_settings.write_text(json.dumps({"allowNonWorkspaceAccess": True}))

    # Point HOME to isolated_home
    monkeypatch.setenv("HOME", str(isolated_home))
    monkeypatch.setenv("ANTIGRAVITY_OAUTH_TOKEN", token_payload)

    host, port = mqtt_broker

    monkeypatch.setenv("MQTT_HOST", host)
    monkeypatch.setenv("MQTT_PORT", str(port))
    monkeypatch.setenv("MQTT_PROMPT_TOPIC", "test/e2e_prompt_agy_isolated")
    monkeypatch.setenv("AI_BACKEND", "agy")
    monkeypatch.setenv("AGY_TIMEOUT_SECONDS", "120")
    monkeypatch.setenv("AGY_DANGEROUSLY_SKIP_PERMISSIONS", "true")

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

        response_topic = "test/e2e_response_agy_isolated"
        test_client.subscribe(response_topic)
        time.sleep(0.5)

        test_file = tmp_path / "secret_agy_isolated.txt"
        test_file.write_text("The secret code is PINEAPPLE.")

        payload = {
            "response_topic": response_topic,
            "prompt": "Read the attached text document and output exactly the secret code word found inside it. Do not say anything else.",
            "files": [str(test_file)]
        }
        test_client.publish(config.mqtt_prompt_topic, json.dumps(payload))

        start_time = time.time()
        while time.time() - start_time < 120:
            if received_messages:
                break
            time.sleep(0.5)

        assert len(received_messages) > 0, "Timeout: No response received from isolated agy CLI"
        response_text = received_messages[0].upper()
        print(f'Received response: {response_text}')
        assert "PINEAPPLE" in response_text, f"Expected 'PINEAPPLE' in response, got: {received_messages[0]}"

    finally:
        test_client.loop_stop()
        test_client.disconnect()
        app.stop()


# Alias for backward compatibility
test_real_agy_cli_integration = test_real_agy_cli_integration_mounted_config



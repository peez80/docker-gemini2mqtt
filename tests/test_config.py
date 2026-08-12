import os
import pytest
from config import load_config

def test_load_config_defaults(monkeypatch):
    monkeypatch.delenv("MQTT_HOST", raising=False)
    monkeypatch.delenv("MQTT_PORT", raising=False)
    monkeypatch.setenv("MQTT_PROMPT_TOPIC", "test/topic")
    
    config = load_config()
    assert config.mqtt_host == "localhost"
    assert config.mqtt_port == 1883
    assert config.mqtt_prompt_topic == "test/topic"
    assert config.gemini_max_concurrent == 2
    assert config.gemini_retry_count == 3
    assert config.ai_backend == "gemini"
    assert config.vertex_project is None
    assert config.vertex_location == "global"

def test_load_config_vertex_backend(monkeypatch):
    monkeypatch.setenv("MQTT_PROMPT_TOPIC", "test/topic")
    monkeypatch.setenv("AI_BACKEND", "vertex")
    monkeypatch.setenv("VERTEX_GOOGLE_CLOUD_PROJECT", "my-project")
    monkeypatch.setenv("VERTEX_GOOGLE_CLOUD_LOCATION", "europe-west3")
    
    config = load_config()
    assert config.ai_backend == "vertex"
    assert config.vertex_project == "my-project"
    assert config.vertex_location == "europe-west3"

def test_load_config_vertex_missing_project(monkeypatch):
    monkeypatch.setenv("MQTT_PROMPT_TOPIC", "test/topic")
    monkeypatch.setenv("AI_BACKEND", "vertex")
    # missing VERTEX_GOOGLE_CLOUD_PROJECT should sys.exit(1)
    with pytest.raises(SystemExit):
        load_config()

def test_load_config_agy_backend_defaults(monkeypatch):
    monkeypatch.setenv("MQTT_PROMPT_TOPIC", "test/topic")
    monkeypatch.setenv("AI_BACKEND", "agy")
    monkeypatch.delenv("AGY_BINARY_PATH", raising=False)
    monkeypatch.delenv("AGY_MODEL", raising=False)
    monkeypatch.delenv("AGY_EFFORT", raising=False)
    monkeypatch.delenv("AGY_TIMEOUT_SECONDS", raising=False)
    monkeypatch.delenv("AGY_DANGEROUSLY_SKIP_PERMISSIONS", raising=False)

    config = load_config()
    assert config.ai_backend == "agy"
    assert config.agy_binary_path == "agy"
    assert config.agy_model is None
    assert config.agy_effort is None
    assert config.agy_timeout_seconds == 120
    assert config.agy_dangerously_skip_permissions is True

def test_load_config_agy_backend_custom(monkeypatch):
    monkeypatch.setenv("MQTT_PROMPT_TOPIC", "test/topic")
    monkeypatch.setenv("AI_BACKEND", "agy")
    monkeypatch.setenv("AGY_BINARY_PATH", "/usr/local/bin/agy")
    monkeypatch.setenv("AGY_MODEL", "gemini-3.6-flash-high")
    monkeypatch.setenv("AGY_EFFORT", "high")
    monkeypatch.setenv("AGY_TIMEOUT_SECONDS", "60")
    monkeypatch.setenv("AGY_DANGEROUSLY_SKIP_PERMISSIONS", "false")

    config = load_config()
    assert config.ai_backend == "agy"
    assert config.agy_binary_path == "/usr/local/bin/agy"
    assert config.agy_model == "gemini-3.6-flash-high"
    assert config.agy_effort == "high"
    assert config.agy_timeout_seconds == 60
    assert config.agy_dangerously_skip_permissions is False

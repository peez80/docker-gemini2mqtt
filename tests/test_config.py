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

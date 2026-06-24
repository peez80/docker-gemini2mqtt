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



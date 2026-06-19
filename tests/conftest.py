import time
import pytest
from testcontainers.core.container import DockerContainer

@pytest.fixture(scope="session")
def mqtt_broker():
    """
    Start a Mosquitto MQTT broker in a Docker container using testcontainers.
    This fixture is session-scoped, so the broker starts once per test run.
    """
    # We use mosquitto 1.6.15 because it allows anonymous connections by default
    # without needing a custom configuration file, making it perfect for tests.
    with DockerContainer("eclipse-mosquitto:1.6.15") as container:
        container.with_exposed_ports(1883)
        container.start()
        
        # Wait briefly for mosquitto to be ready (it starts almost instantly)
        time.sleep(1.0)
        
        host = container.get_container_host_ip()
        port = container.get_exposed_port(1883)
        
        yield host, port

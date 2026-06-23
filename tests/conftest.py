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

def pytest_addoption(parser):
    parser.addoption(
        "--run-e2e", action="store_true", default=False, help="run e2e tests"
    )

def pytest_configure(config):
    config.addinivalue_line("markers", "e2e: mark test as e2e to run")

def pytest_collection_modifyitems(config, items):
    if config.getoption("--run-e2e"):
        # --run-e2e given in cli: do not skip e2e tests
        return
    skip_e2e = pytest.mark.skip(reason="need --run-e2e option to run")
    for item in items:
        if "e2e" in item.keywords:
            item.add_marker(skip_e2e)

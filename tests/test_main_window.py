# tests/test_main_window.py
import pytest
from ui.main_window import MainWindow
from backend.infrastructure.di_container import DIContainer
from backend.infrastructure.configuration_manager import ConfigurationManager

@pytest.fixture
def window():
    config = ConfigurationManager(config={"project_id": "test"})
    container = DIContainer(config)
    app = MainWindow(container)
    yield app
    app.destroy()

def test_startup(window):
    assert window.title() == "Generador gcloud"
    assert window.current_service_name in window.container.list_services()

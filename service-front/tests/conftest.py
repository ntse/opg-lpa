import pytest
from fastapi.testclient import TestClient

from app import create_app


@pytest.fixture(scope="session")
def app_instance():
    return create_app()


@pytest.fixture()
def client(app_instance):
    with TestClient(app_instance) as test_client:
        yield test_client

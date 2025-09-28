from http import HTTPStatus
from pathlib import Path

import pytest

from app.services.content import ContentService


@pytest.mark.parametrize(
    "path, expected_fragment",
    [
        ("/home", "This online service will help you to create a lasting power of attorney"),
        ("/terms", "These terms"),
        ("/accessibility", "This online service is run by"),
        ("/privacy-notice", "This privacy notice explains why the Office of the Public Guardian"),
        ("/contact", "Call 0300 456 0300"),
        ("/cookies", "We use essential cookies"),
        ("/send-feedback", "Send feedback"),
    ],
)
def test_general_pages_render(client, path, expected_fragment):
    response = client.get(path)
    assert response.status_code == HTTPStatus.OK
    assert expected_fragment in response.text


def test_root_redirects_to_home(client):
    response = client.get("/", follow_redirects=False)
    assert response.status_code == HTTPStatus.TEMPORARY_REDIRECT
    assert response.headers["location"] == "/home"


def test_guidance_index_lists_topics(client):
    response = client.get("/guide")
    assert response.status_code == HTTPStatus.OK
    assert "Browse guidance" in response.text


def test_guidance_page_renders_markdown(client):
    guidance_dir = Path(__file__).resolve().parents[1] / "content" / "guidance"
    service = ContentService(guidance_dir.parent)
    page = next(service.iter_guidance_pages())

    response = client.get(f"/guide/{page.slug}")
    assert response.status_code == HTTPStatus.OK
    assert page.title in response.text


def test_unknown_guidance_returns_404(client):
    response = client.get("/guide/not-a-real-page")
    assert response.status_code == HTTPStatus.NOT_FOUND

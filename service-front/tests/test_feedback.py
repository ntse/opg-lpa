from http import HTTPStatus


def test_feedback_submission_redirects(client):
    response = client.post(
        "/send-feedback",
        data={
            "name": "Test User",
            "email": "user@example.org",
            "message": "This service is excellent and easy to use.",
            "consent": "true",
        },
        follow_redirects=False,
    )

    assert response.status_code == HTTPStatus.SEE_OTHER
    assert response.headers["location"] == "/feedback-thanks"


def test_feedback_validation_error(client):
    response = client.post(
        "/send-feedback",
        data={"message": "short"},
    )

    assert response.status_code == HTTPStatus.OK
    assert "Message cannot be empty" in response.text or "at least" in response.text

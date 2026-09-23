import base64

import httpx
import pytest

from app.ekt_client import EktBadResponse, EktClient, EktTimeout


def make_client(handler) -> EktClient:
    return EktClient(
        base_url="https://ekt.test/api",
        username="user",
        password="password",
        timeout=0.01,
        transport=httpx.MockTransport(handler),
    )


def test_basic_auth_and_one_retry_after_timeout():
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if len(requests) == 1:
            raise httpx.ReadTimeout("slow", request=request)
        return httpx.Response(
            200,
            json={"page": 1, "per_page": 10, "count": 0, "items": []},
        )

    client = make_client(handler)
    try:
        response = client.list_products(1)
    finally:
        client.close()

    assert response["items"] == []
    assert len(requests) == 2
    expected = base64.b64encode(b"user:password").decode()
    assert requests[0].headers["Authorization"] == f"Basic {expected}"


def test_second_timeout_is_reported_as_timeout():
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        raise httpx.ReadTimeout("slow", request=request)

    client = make_client(handler)
    with pytest.raises(EktTimeout):
        client.list_products(1)
    client.close()
    assert calls == 2


def test_invalid_json_is_bad_response():
    client = make_client(lambda request: httpx.Response(200, text="not-json"))
    with pytest.raises(EktBadResponse):
        client.list_products(1)
    client.close()


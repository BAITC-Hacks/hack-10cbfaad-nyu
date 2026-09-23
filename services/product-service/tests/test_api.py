from copy import deepcopy

from app.ekt_client import EktTimeout
from app.models import Product
from app.service import upsert_product


def seed(db, payload, *, sync_id="seed"):
    product = upsert_product(db, payload, sync_id=sync_id, is_detail=True)
    db.commit()
    return product


def analog_payload(fixture_product):
    payload = deepcopy(fixture_product)
    payload.update(
        {
            "id": 515292,
            "article": "200300286_",
            "name": "027103 АВ DRX250 MT 3ф 200А 18ka Legrand (1)",
            "description": "Автоматический выключатель DRX250 MT 3P 200А 18kA 400V",
            "price": 69880,
            "quantity": 4,
        }
    )
    payload["properties"] = dict(payload["properties"])
    payload["properties"].update(
        {"ARTIKULPOSTAVSHCHIKA": "027103", "NOMINALNYY_TOK": "200 А"}
    )
    return payload


def test_health_and_internal_authentication(client):
    assert client.get("/health").json() == {"status": "healthy"}

    unauthorized = client.post(
        "/internal/v1/products/search",
        json={"query": "027228"},
    )
    assert unauthorized.status_code == 401
    assert unauthorized.json()["error"]["code"] == "UNAUTHORIZED"
    assert unauthorized.headers["X-Request-ID"]


def test_current_ai_service_token_header_is_supported(client, db, fixture_product):
    seed(db, fixture_product)
    response = client.post(
        "/internal/v1/products/search",
        headers={"X-Internal-Service-Token": "test-token"},
        json={"query": "027228"},
    )
    assert response.status_code == 200
    assert response.json()["items"][0]["product"]["id"] == 515291


def test_search_priority_filters_and_empty_result(
    client, db, fixture_product, auth_headers
):
    seed(db, fixture_product)

    exact = client.post(
        "/internal/v1/products/search",
        headers=auth_headers,
        json={"query": "027228", "filters": {}, "limit": 5},
    )
    assert exact.status_code == 200
    assert exact.json()["items"][0]["match_score"] == 0.99
    assert exact.json()["items"][0]["product"]["price"]["status"] == "cached"

    filtered = client.post(
        "/internal/v1/products/search",
        headers=auth_headers,
        json={
            "query": "027228",
            "filters": {"brand": "Legrand", "poles": 3, "in_stock": True},
        },
    )
    assert filtered.status_code == 200
    assert filtered.json()["total_returned"] == 1

    empty = client.post(
        "/internal/v1/products/search",
        headers=auth_headers,
        json={"query": "nonexistent xyz"},
    )
    assert empty.status_code == 200
    assert empty.json() == {
        "query": "nonexistent xyz",
        "items": [],
        "total_returned": 0,
    }


def test_search_accepts_natural_language_around_article(
    client, db, fixture_product, auth_headers
):
    seed(db, fixture_product)

    response = client.post(
        "/internal/v1/products/search",
        headers=auth_headers,
        json={"query": "Найди товар 027228"},
    )

    assert response.status_code == 200
    assert response.json()["items"][0]["product"]["id"] == 515291
    assert response.json()["items"][0]["match_score"] == 0.99


def test_search_understands_lamp_bulb_alias(client, db, fixture_product, auth_headers):
    lamp = deepcopy(fixture_product)
    lamp.update(
        {
            "id": 515293,
            "article": "LAMP-10W",
            "name": "Лампа светодиодная 10 Вт E27",
            "description": "Светодиодная лампа для внутреннего освещения",
        }
    )
    seed(db, lamp)

    response = client.post(
        "/internal/v1/products/search",
        headers=auth_headers,
        json={"query": "лампочка"},
    )

    assert response.status_code == 200
    assert response.json()["items"][0]["product"]["id"] == 515293


def test_live_detail_and_availability(client, ekt, fixture_product, auth_headers):
    ekt.details[515291] = fixture_product

    detail = client.get(
        "/internal/v1/products/515291", headers=auth_headers
    )
    assert detail.status_code == 200
    product = detail.json()["product"]
    assert product["price"]["status"] == "live"
    assert product["availability"]["status"] == "live"
    assert product["availability"]["quantity_total"] == 23
    assert product["specs"]["nominal_current_a"] is None
    assert product["data_quality"]["has_conflicts"] is True

    availability = client.get(
        "/internal/v1/products/515291/availability", headers=auth_headers
    )
    assert availability.status_code == 200
    assert availability.json()["status"] == "live"
    assert availability.json()["stores"][1]["name"] == "Алматы"


def test_live_availability_never_falls_back_to_cache(
    client, db, ekt, fixture_product, auth_headers
):
    seed(db, fixture_product)
    ekt.detail_error = EktTimeout("timeout")

    response = client.get(
        "/internal/v1/products/515291/availability", headers=auth_headers
    )
    assert response.status_code == 504
    assert response.json()["error"]["code"] == "UPSTREAM_TIMEOUT"
    assert "quantity_total" not in response.json()["error"]


def test_analog_candidates_have_differences(
    client, db, fixture_product, auth_headers
):
    seed(db, fixture_product)
    seed(db, analog_payload(fixture_product))

    response = client.post(
        "/internal/v1/products/515291/analogs",
        headers=auth_headers,
        json={"limit": 3, "require_in_stock": True},
    )
    assert response.status_code == 200
    item = response.json()["items"][0]
    assert item["compatibility_status"] == "candidate"
    assert item["product"]["id"] == 515292
    assert any(
        difference["field"] == "nominal_current_a"
        for difference in item["different_fields"]
    )


def test_sync_stops_on_repeated_product_ids(
    client, ekt, fixture_product, auth_headers
):
    list_item = {
        key: fixture_product[key]
        for key in ("id", "name", "article", "price", "image", "url", "offers")
    }
    ekt.pages = {
        1: {"page": 1, "per_page": 1, "count": 1, "items": [list_item]},
        2: {"page": 2, "per_page": 1, "count": 1, "items": [list_item]},
    }

    response = client.post(
        "/internal/v1/catalog/sync",
        headers=auth_headers,
        json={"enrich_details": False},
    )
    assert response.status_code == 200
    result = response.json()
    assert result["complete"] is False
    assert result["products_seen"] == 1
    assert result["stopped_reason"] == "repeated_product_ids"


def test_complete_sync_deactivates_unseen_products(
    client, db, ekt, fixture_product, auth_headers
):
    old = analog_payload(fixture_product)
    seed(db, old, sync_id="old-sync")
    list_item = {
        key: fixture_product[key]
        for key in ("id", "name", "article", "price", "image", "url", "offers")
    }
    ekt.pages = {
        1: {"page": 1, "per_page": 2, "count": 1, "items": [list_item]}
    }

    response = client.post(
        "/internal/v1/catalog/sync",
        headers=auth_headers,
        json={"enrich_details": False},
    )
    assert response.status_code == 200
    assert response.json()["complete"] is True
    db.expire_all()
    assert db.get(Product, 515292).is_active is False
    assert db.get(Product, 515291).is_active is True


def test_validation_uses_common_error_shape(client, auth_headers):
    response = client.post(
        "/internal/v1/products/search",
        headers=auth_headers,
        json={"query": " ", "limit": 100},
    )
    assert response.status_code == 422
    payload = response.json()["error"]
    assert payload["code"] == "VALIDATION_ERROR"
    assert payload["retryable"] is False
    assert payload["request_id"] == auth_headers["X-Request-ID"]


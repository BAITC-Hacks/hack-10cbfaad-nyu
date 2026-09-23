from typing import Any

import httpx


class EktClientError(Exception):
    pass


class EktBadResponse(EktClientError):
    pass


class EktUnavailable(EktClientError):
    pass


class EktTimeout(EktClientError):
    pass


class EktProductNotFound(EktClientError):
    pass


class EktClient:
    RETRYABLE_STATUSES = {502, 503, 504}

    def __init__(
        self,
        *,
        base_url: str,
        username: str,
        password: str,
        timeout: float,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.username = username
        self.password = password
        self.client = httpx.Client(
            base_url=base_url.rstrip("/") + "/",
            auth=httpx.BasicAuth(username, password),
            timeout=timeout,
            transport=transport,
            headers={"Accept": "application/json"},
        )

    def close(self) -> None:
        self.client.close()

    def _get(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        if not self.username or not self.password:
            raise EktUnavailable("ekt.kz Product API credentials are not configured")

        for attempt in range(2):
            try:
                response = self.client.get(path, params=params)
            except httpx.TimeoutException as exc:
                if attempt == 0:
                    continue
                raise EktTimeout("ekt.kz Product API request timed out") from exc
            except httpx.RequestError as exc:
                raise EktUnavailable("ekt.kz Product API is unavailable") from exc

            if response.status_code == 404:
                raise EktProductNotFound("product was not found by ekt.kz")
            if response.status_code in self.RETRYABLE_STATUSES:
                if attempt == 0:
                    continue
                raise EktUnavailable(
                    f"ekt.kz Product API returned HTTP {response.status_code}"
                )
            if response.status_code >= 400:
                raise EktBadResponse(
                    f"ekt.kz Product API returned HTTP {response.status_code}"
                )
            try:
                payload = response.json()
            except ValueError as exc:
                raise EktBadResponse("ekt.kz Product API returned invalid JSON") from exc
            if not isinstance(payload, dict):
                raise EktBadResponse("ekt.kz Product API returned a non-object response")
            return payload

        raise AssertionError("unreachable")

    def list_products(self, page: int) -> dict[str, Any]:
        payload = self._get("products", {"page": page})
        items = payload.get("items")
        per_page = payload.get("per_page")
        if not isinstance(items, list) or not isinstance(per_page, int) or per_page < 1:
            raise EktBadResponse(
                "ekt.kz catalog response requires items[] and positive per_page"
            )
        if any(not isinstance(item, dict) for item in items):
            raise EktBadResponse("ekt.kz catalog items must be objects")
        return payload

    def get_product(self, product_id: int) -> dict[str, Any]:
        payload = self._get("products/detail", {"id": product_id})
        returned_id = payload.get("id")
        try:
            id_matches = int(returned_id) == product_id
        except (TypeError, ValueError):
            id_matches = False
        if not id_matches or not isinstance(payload.get("name"), str):
            raise EktBadResponse(
                "ekt.kz product detail response has an invalid id or name"
            )
        return payload


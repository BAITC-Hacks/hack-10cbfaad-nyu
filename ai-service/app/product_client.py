from typing import Any

import httpx


class ProductServiceError(Exception):
    pass


class ProductClient:
    def __init__(self, base_url: str, token: str, timeout: float = 10):
        self.base_url = base_url.rstrip("/")
        self.headers = {"X-Internal-Service-Token": token}
        self.timeout = timeout

    async def search_products(self, query: str, filters: dict[str, Any] | None = None, limit: int = 5) -> dict[str, Any]:
        return await self._request("POST", "/internal/v1/products/search", json={"query": query, "filters": filters or {}, "limit": limit})

    async def get_product(self, product_id: int) -> dict[str, Any]:
        return await self._request("GET", f"/internal/v1/products/{product_id}")

    async def find_analogs(self, product_id: int, limit: int = 5) -> dict[str, Any]:
        return await self._request("POST", f"/internal/v1/products/{product_id}/analogs", json={"limit": limit})

    async def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.request(method, self.base_url + path, headers=self.headers, **kwargs)
            if response.status_code >= 500:
                raise ProductServiceError("Product Service unavailable")
            response.raise_for_status()
            return response.json()
        except (httpx.HTTPError, ProductServiceError) as exc:
            raise ProductServiceError(str(exc)) from exc

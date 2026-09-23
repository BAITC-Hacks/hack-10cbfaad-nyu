# Product Service

FastAPI service responsible for the normalized ekt.kz catalog, product search,
live product details and warehouse availability, and analog candidates.

## Run locally with Docker

Copy `.env.example` to `.env` and set `EKT_API_USERNAME` and
`EKT_API_PASSWORD` when live ekt.kz requests are needed. Never commit `.env`.

```powershell
docker compose -f compose.yml up --build product-service
```

The service listens on `http://localhost:8001`. Health is available without
internal authentication:

```powershell
Invoke-RestMethod http://localhost:8001/health
```

Internal endpoints accept the architecture's Bearer token. The
`X-Internal-Service-Token` form is also accepted for compatibility with the
current AI Service client.

```powershell
$headers = @{ Authorization = "Bearer change-me" }
$body = @{ query = "027228"; limit = 5; filters = @{} } | ConvertTo-Json
Invoke-RestMethod -Method Post `
  -Uri http://localhost:8001/internal/v1/products/search `
  -Headers $headers -ContentType application/json -Body $body
```

## Synchronize the catalog

Run a full catalog synchronization inside the running container:

```powershell
docker compose -f compose.yml exec product-service python -m app.sync_catalog
```

For a list-only import, add `--no-enrich`. The same operation is available as
`POST /internal/v1/catalog/sync` with this optional body:

```json
{"enrich_details": true, "max_pages": null}
```

The service never synchronizes automatically during startup.

To populate local PostgreSQL with the documented conflict fixture without
ekt.kz credentials:

```powershell
docker compose -f compose.yml exec product-service python -m app.load_fixture
```

## Tests

The test profile uses the same PostgreSQL service:

```powershell
docker compose -f compose.yml --profile test build tests
docker compose -f compose.yml --profile test run --rm tests
```

from datetime import datetime
import re
from typing import Any
from uuid import uuid4

from sqlalchemy import Select, and_, func, or_, select, text, update
from sqlalchemy.orm import Session

from .ekt_client import (
    EktBadResponse,
    EktClient,
    EktProductNotFound,
    EktTimeout,
    EktUnavailable,
)
from .errors import ServiceError, product_not_found
from .models import Product
from .normalizer import iso_z, normalize_product, utc_now
from .schemas import AnalogRequest, SearchRequest, SyncRequest


SEARCH_STOP_WORDS = {
    "find",
    "please",
    "product",
    "search",
    "дайте",
    "ищу",
    "купить",
    "мне",
    "найди",
    "найдите",
    "нужен",
    "нужна",
    "нужно",
    "нужны",
    "пожалуйста",
    "покажи",
    "покажите",
    "товар",
    "хочу",
}
SEARCH_ALIASES = {
    "bulb": {"lamp", "лампа"},
    "лампочка": {"лампа"},
    "лампочки": {"лампа"},
    "лампочку": {"лампа"},
}
SEARCH_TOKEN_PATTERN = re.compile(r"[\w]+(?:[./-][\w]+)*", re.UNICODE)


def _query_groups(query: str) -> list[set[str]]:
    tokens = [token.casefold() for token in SEARCH_TOKEN_PATTERN.findall(query)]
    significant = [token for token in tokens if token not in SEARCH_STOP_WORDS]
    selected = significant or tokens
    return [{token, *SEARCH_ALIASES.get(token, set())} for token in selected]


def map_ekt_error(error: Exception, product_id: int | None = None) -> ServiceError:
    if isinstance(error, EktProductNotFound) and product_id is not None:
        return product_not_found(product_id)
    if isinstance(error, EktTimeout):
        return ServiceError(
            504,
            "UPSTREAM_TIMEOUT",
            "ekt.kz Product API request timed out",
            retryable=True,
        )
    if isinstance(error, EktUnavailable):
        return ServiceError(
            503,
            "UPSTREAM_CATALOG_UNAVAILABLE",
            "ekt.kz Product API is unavailable",
            retryable=True,
        )
    return ServiceError(
        502,
        "UPSTREAM_BAD_RESPONSE",
        "ekt.kz Product API returned an unusable response",
        retryable=True,
    )


PRODUCT_COLUMNS = (
    "article",
    "supplier_article",
    "barcode",
    "name",
    "description",
    "brand",
    "product_type",
    "poles",
    "nominal_current_a",
    "breaking_capacity_ka",
    "nominal_voltage_v",
    "installation_type",
    "price_amount",
    "quantity_total",
    "stores",
    "offers",
    "image_url",
    "product_url",
    "properties_raw",
    "raw_payload",
    "has_conflicts",
    "warnings",
    "search_text",
)


def upsert_product(
    session: Session,
    payload: dict[str, Any],
    *,
    sync_id: str | None = None,
    is_detail: bool = False,
) -> Product:
    try:
        product_id = int(payload.get("id"))
    except (TypeError, ValueError) as exc:
        raise EktBadResponse("product payload has an invalid id") from exc

    product = session.get(Product, product_id)
    merged_payload: dict[str, Any] = {}
    if product is not None and not is_detail:
        merged_payload.update(product.raw_payload or {})
    merged_payload.update(payload)

    try:
        normalized = normalize_product(merged_payload)
    except ValueError as exc:
        raise EktBadResponse(str(exc)) from exc

    if product is None:
        product = Product(id=normalized["id"])
        session.add(product)
    for column in PRODUCT_COLUMNS:
        setattr(product, column, normalized[column])
    product.is_active = True
    now = utc_now()
    if sync_id is not None:
        product.last_seen_sync_id = sync_id
        product.synced_at = now
    if is_detail:
        product.detail_fetched_at = now
    session.flush()
    return product


def _json_number(value: float | None) -> int | float | None:
    if value is None:
        return None
    return int(value) if value.is_integer() else value


def product_view(
    product: Product,
    *,
    freshness: str = "cached",
    verified_at: datetime | None = None,
) -> dict[str, Any]:
    verified = iso_z(verified_at) if verified_at is not None else None
    return {
        "id": product.id,
        "article": product.article,
        "supplier_article": product.supplier_article,
        "barcode": product.barcode,
        "name": product.name,
        "brand": product.brand,
        "product_type": product.product_type,
        "description": product.description,
        "specs": {
            "poles": product.poles,
            "nominal_current_a": _json_number(product.nominal_current_a),
            "breaking_capacity_ka": _json_number(product.breaking_capacity_ka),
            "nominal_voltage_v": _json_number(product.nominal_voltage_v),
            "installation_type": product.installation_type,
        },
        "price": {
            "amount": product.price_amount,
            "currency": "KZT",
            "status": freshness,
            "verified_at": verified,
        },
        "availability": {
            "status": freshness,
            "quantity_total": product.quantity_total,
            "verified_at": verified,
            "stores": product.stores or [],
        },
        "image_url": product.image_url,
        "product_url": product.product_url,
        "offers": product.offers or [],
        "certificates": {"status": "unknown", "items": []},
        "data_quality": {
            "has_conflicts": product.has_conflicts,
            "warnings": product.warnings or [],
        },
        "properties_raw": product.properties_raw or {},
    }


def _apply_filters(statement: Select[Any], request: SearchRequest) -> Select[Any]:
    filters = request.filters
    if filters.brand is not None:
        statement = statement.where(func.lower(Product.brand) == filters.brand.casefold())
    if filters.product_type is not None:
        statement = statement.where(
            func.lower(Product.product_type) == filters.product_type.casefold()
        )
    if filters.supplier_article is not None:
        statement = statement.where(Product.supplier_article == filters.supplier_article)
    if filters.barcode is not None:
        statement = statement.where(Product.barcode == filters.barcode)
    if filters.poles is not None:
        statement = statement.where(Product.poles == filters.poles)
    if filters.nominal_current_a is not None:
        statement = statement.where(
            Product.nominal_current_a == filters.nominal_current_a
        )
    if filters.breaking_capacity_ka is not None:
        statement = statement.where(
            Product.breaking_capacity_ka == filters.breaking_capacity_ka
        )
    if filters.nominal_voltage_v is not None:
        statement = statement.where(
            Product.nominal_voltage_v == filters.nominal_voltage_v
        )
    if filters.in_stock is True:
        statement = statement.where(Product.quantity_total > 0)
    elif filters.in_stock is False:
        statement = statement.where(Product.quantity_total == 0)
    return statement


def _score_product(product: Product, request: SearchRequest) -> tuple[float, list[str]]:
    query = request.query.casefold()
    query_groups = _query_groups(query)
    query_terms = set().union(*query_groups) if query_groups else set()
    reasons: list[str] = []

    if product.article and product.article.casefold() in query_terms | {query}:
        return 1.0, ["exact article matched"]
    if product.supplier_article and product.supplier_article.casefold() in query_terms | {query}:
        return 0.99, ["exact supplier article matched"]
    if product.barcode and product.barcode.casefold() in query_terms | {query}:
        return 0.98, ["exact barcode matched"]

    score = 0.0
    name = product.name.casefold()
    search_text = (product.search_text or "").casefold()
    if name == query:
        score = 0.92
        reasons.append("exact product name matched")
    elif query in name:
        score = 0.85
        reasons.append("query found in product name")
    elif query_groups:
        matched_groups = [
            group for group in query_groups if any(term in search_text for term in group)
        ]
        ratio = len(matched_groups) / len(query_groups)
        if ratio:
            score = 0.45 + 0.35 * ratio
            reasons.append(f"{len(matched_groups)} query terms matched")

    for label, value in (
        ("article", product.article),
        ("supplier article", product.supplier_article),
        ("barcode", product.barcode),
    ):
        if value and value.casefold() in query:
            score = max(score, 0.8)
            reasons.append(f"{label} {value} matched")
    if product.brand and product.brand.casefold() in query:
        score = min(0.97, score + 0.05)
        reasons.append(f"brand {product.brand} matched")

    filters = request.filters.model_dump(exclude_none=True)
    for field, expected in filters.items():
        if field == "in_stock":
            reasons.append("stock filter matched")
        else:
            reasons.append(f"{field}={expected} filter matched")
        score = min(0.97, score + 0.02)
    return round(score, 4), list(dict.fromkeys(reasons))


def search_products(session: Session, request: SearchRequest) -> dict[str, Any]:
    query = request.query.casefold()
    like = f"%{query}%"
    candidate_conditions = [
        func.lower(Product.article) == query,
        func.lower(Product.supplier_article) == query,
        func.lower(Product.barcode) == query,
        func.lower(Product.name).like(like),
        func.lower(Product.search_text).like(like),
    ]
    for group in _query_groups(query):
        for term in group:
            term_like = f"%{term}%"
            candidate_conditions.extend(
                [
                    func.lower(Product.article) == term,
                    func.lower(Product.supplier_article) == term,
                    func.lower(Product.barcode) == term,
                    func.lower(Product.name).like(term_like),
                    func.lower(Product.search_text).like(term_like),
                ]
            )
    if session.bind is not None and session.bind.dialect.name == "postgresql":
        candidate_conditions.append(
            text(
                "to_tsvector('simple', coalesce(search_text, '')) "
                "@@ plainto_tsquery('simple', :fts_query)"
            ).bindparams(fts_query=request.query)
        )
    statement = select(Product).where(
        and_(Product.is_active.is_(True), or_(*candidate_conditions))
    )
    statement = _apply_filters(statement, request).limit(500)
    products = session.scalars(statement).all()
    scored = [(*_score_product(product, request), product) for product in products]
    scored = [item for item in scored if item[0] > 0]
    scored.sort(key=lambda item: (-item[0], item[2].id))
    items = [
        {
            "product": product_view(product),
            "match_score": score,
            "match_reasons": reasons,
        }
        for score, reasons, product in scored[: request.limit]
    ]
    return {"query": request.query, "items": items, "total_returned": len(items)}


def get_live_product(
    session: Session, client: EktClient, product_id: int
) -> dict[str, Any]:
    try:
        payload = client.get_product(product_id)
        verified_at = utc_now()
        product = upsert_product(session, payload, is_detail=True)
        session.commit()
    except (EktBadResponse, EktUnavailable, EktTimeout, EktProductNotFound) as exc:
        session.rollback()
        raise map_ekt_error(exc, product_id) from exc
    return {"product": product_view(product, freshness="live", verified_at=verified_at)}


def get_live_availability(
    session: Session, client: EktClient, product_id: int
) -> dict[str, Any]:
    result = get_live_product(session, client, product_id)
    availability = result["product"]["availability"]
    return {
        "product_id": product_id,
        "status": "live",
        "quantity_total": availability["quantity_total"],
        "verified_at": availability["verified_at"],
        "stores": availability["stores"],
    }


ANALOG_FIELDS = (
    ("brand", 0.15),
    ("product_type", 0.25),
    ("poles", 0.15),
    ("breaking_capacity_ka", 0.15),
    ("nominal_voltage_v", 0.10),
    ("installation_type", 0.10),
    ("nominal_current_a", 0.10),
)


def find_analogs(
    session: Session, product_id: int, request: AnalogRequest
) -> dict[str, Any]:
    source = session.get(Product, product_id)
    if source is None or not source.is_active:
        raise product_not_found(product_id)

    statement = select(Product).where(
        Product.is_active.is_(True), Product.id != product_id
    )
    if source.product_type:
        statement = statement.where(
            func.lower(Product.product_type) == source.product_type.casefold()
        )
    if request.require_in_stock:
        statement = statement.where(Product.quantity_total > 0)
    candidates = session.scalars(statement.limit(500)).all()

    ranked: list[tuple[float, Product, list[str], list[dict[str, Any]]]] = []
    for candidate in candidates:
        score = 0.0
        matched: list[str] = []
        different: list[dict[str, Any]] = []
        for field, weight in ANALOG_FIELDS:
            source_value = getattr(source, field)
            candidate_value = getattr(candidate, field)
            if source_value is not None and candidate_value is not None:
                if source_value == candidate_value:
                    score += weight
                    matched.append(field)
                else:
                    different.append(
                        {
                            "field": field,
                            "source_value": source_value,
                            "candidate_value": candidate_value,
                        }
                    )
            elif source_value != candidate_value:
                different.append(
                    {
                        "field": field,
                        "source_value": source_value,
                        "candidate_value": candidate_value,
                    }
                )
        ranked.append((round(score, 4), candidate, matched, different))

    ranked.sort(key=lambda item: (-item[0], item[1].id))
    return {
        "source_product_id": product_id,
        "items": [
            {
                "product": product_view(candidate),
                "compatibility_status": "candidate",
                "score": score,
                "matched_fields": matched,
                "different_fields": different,
            }
            for score, candidate, matched, different in ranked[: request.limit]
        ],
    }


def sync_catalog(
    session: Session, client: EktClient, request: SyncRequest
) -> dict[str, Any]:
    sync_id = str(uuid4())
    seen: set[int] = set()
    failed: list[int] = []
    pages_processed = 0
    upserted = 0
    enriched = 0
    complete = False
    stopped_reason = "unknown"
    page = 1

    while True:
        if request.max_pages is not None and page > request.max_pages:
            stopped_reason = "max_pages_reached"
            break
        try:
            response = client.list_products(page)
        except (EktBadResponse, EktUnavailable, EktTimeout, EktProductNotFound) as exc:
            session.rollback()
            raise map_ekt_error(exc) from exc

        pages_processed += 1
        items = response["items"]
        per_page = response["per_page"]
        if not items:
            complete = True
            stopped_reason = "empty_page"
            break

        page_ids: list[int] = []
        repeated = False
        for item in items:
            try:
                product_id = int(item.get("id"))
            except (TypeError, ValueError) as exc:
                session.rollback()
                raise map_ekt_error(EktBadResponse("catalog item has invalid id")) from exc
            if product_id in seen:
                repeated = True
                continue
            seen.add(product_id)
            page_ids.append(product_id)
            try:
                upsert_product(session, item, sync_id=sync_id)
            except EktBadResponse as exc:
                session.rollback()
                raise map_ekt_error(exc) from exc
            upserted += 1
        session.commit()

        if request.enrich_details:
            for product_id in page_ids:
                try:
                    detail = client.get_product(product_id)
                    upsert_product(
                        session, detail, sync_id=sync_id, is_detail=True
                    )
                    session.commit()
                    enriched += 1
                except EktProductNotFound:
                    session.rollback()
                    failed.append(product_id)
                except (EktBadResponse, EktUnavailable, EktTimeout):
                    session.rollback()
                    failed.append(product_id)

        if repeated:
            stopped_reason = "repeated_product_ids"
            break
        if len(items) < per_page:
            complete = True
            stopped_reason = "short_page"
            break
        page += 1

    if complete:
        session.execute(
            update(Product)
            .where(
                or_(
                    Product.last_seen_sync_id.is_(None),
                    Product.last_seen_sync_id != sync_id,
                )
            )
            .values(is_active=False)
        )
        session.commit()

    return {
        "sync_id": sync_id,
        "complete": complete,
        "pages_processed": pages_processed,
        "products_seen": len(seen),
        "products_upserted": upserted,
        "details_enriched": enriched,
        "failed_product_ids": failed,
        "stopped_reason": stopped_reason,
    }


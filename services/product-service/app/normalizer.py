import re
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Callable


NUMBER = r"(\d+(?:[.,]\d+)?)"
CURRENT_RE = re.compile(rf"{NUMBER}\s*(?:a|а)(?![a-zа-я])", re.IGNORECASE)
BREAKING_RE = re.compile(rf"{NUMBER}\s*(?:ka|kа|кa|ка)(?![a-zа-я])", re.IGNORECASE)
VOLTAGE_RE = re.compile(rf"{NUMBER}\s*(?:vac|v|в)(?![a-zа-я])", re.IGNORECASE)
POLES_RE = re.compile(
    rf"{NUMBER}\s*(?:p|poles?|полюс(?:а|ов)?|ф)(?![a-zа-я])", re.IGNORECASE
)


PROPERTY_KEYS = {
    "supplier_article": "ARTIKULPOSTAVSHCHIKA",
    "barcode": "CML2_BAR_CODE",
    "brand": "TORGOVAYA_MARKA",
    "product_type": "OBYEM",
    "poles": "KOLICHESTVO_POLYUSOV",
    "current": "NOMINALNYY_TOK",
    "breaking": "NOMINALNAYA_OTKLYUCHAYUSHCHAYA_SPOSOBNOST",
    "voltage": "NOMINALNOE_NAPRYAZHENIE",
    "installation": "TIP_USTANOVKI",
}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso_z(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, dict):
        for key in ("value", "VALUE", "name", "NAME"):
            if key in value:
                return _text(value[key])
        return None
    if isinstance(value, list):
        parts = [item for item in (_text(entry) for entry in value) if item]
        return ", ".join(parts) if parts else None
    result = str(value).strip()
    return result or None


def property_text(properties: dict[str, Any], key: str) -> str | None:
    return _text(properties.get(key))


def _decimal(raw: str | None) -> float | None:
    if raw is None:
        return None
    try:
        return float(Decimal(raw.replace(" ", "").replace(",", ".")))
    except (InvalidOperation, ValueError):
        return None


def _measure(value: str | None, pattern: re.Pattern[str], allow_plain: bool) -> float | None:
    if not value:
        return None
    match = pattern.search(value)
    if match:
        return _decimal(match.group(1))
    if allow_plain:
        match = re.fullmatch(r"\s*(\d+(?:[.,]\d+)?)\s*", value)
        if match:
            return _decimal(match.group(1))
    return None


def parse_current(value: str | None, allow_plain: bool = False) -> float | None:
    return _measure(value, CURRENT_RE, allow_plain)


def parse_breaking_capacity(value: str | None, allow_plain: bool = False) -> float | None:
    return _measure(value, BREAKING_RE, allow_plain)


def parse_voltage(value: str | None, allow_plain: bool = False) -> float | None:
    return _measure(value, VOLTAGE_RE, allow_plain)


def parse_poles(value: str | None, allow_plain: bool = False) -> int | None:
    number = _measure(value, POLES_RE, allow_plain)
    if number is None or not number.is_integer() or number < 1:
        return None
    return int(number)


def _integer(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    text = _text(value)
    if text is None:
        return None
    number = _decimal(text)
    if number is None or not number.is_integer():
        return None
    return int(number)


def _price(value: Any) -> int | None:
    return _integer(value)


def _normal_number(value: float | None) -> int | float | None:
    if value is None:
        return None
    return int(value) if value.is_integer() else value


def _resolve_measure(
    *,
    field: str,
    property_source: str,
    property_value: str | None,
    name: str,
    description: str | None,
    parser: Callable[[str | None, bool], float | int | None],
) -> tuple[float | int | None, dict[str, Any] | None]:
    candidates: list[tuple[str, str, float | int]] = []
    for source, raw, allow_plain in (
        (property_source, property_value, True),
        ("name", name, False),
        ("description", description, False),
    ):
        parsed = parser(raw, allow_plain)
        if parsed is not None and raw is not None:
            candidates.append((source, raw, parsed))

    distinct = {float(item[2]) for item in candidates}
    if len(distinct) > 1:
        return None, {
            "code": "CONFLICTING_FIELD_VALUES",
            "field": field,
            "severity": "warning",
            "values": [
                {"source": source, "value": raw} for source, raw, _ in candidates
            ],
        }
    return (candidates[0][2] if candidates else None), None


def _normalize_stores(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    stores: list[dict[str, Any]] = []
    for raw in value:
        if not isinstance(raw, dict):
            continue
        store_id = _integer(raw.get("id", raw.get("ID")))
        name = _text(raw.get("name", raw.get("NAME")))
        quantity = _integer(raw.get("quantity", raw.get("QUANTITY")))
        if store_id is None or name is None or quantity is None:
            continue
        stores.append({"id": store_id, "name": name, "quantity": quantity})
    return stores


def normalize_product(payload: dict[str, Any]) -> dict[str, Any]:
    product_id = _integer(payload.get("id"))
    name = _text(payload.get("name"))
    if product_id is None or name is None:
        raise ValueError("product payload requires integer id and non-empty name")

    description = _text(payload.get("description"))
    raw_properties = payload.get("properties")
    properties = raw_properties if isinstance(raw_properties, dict) else {}

    warnings: list[dict[str, Any]] = []
    poles, warning = _resolve_measure(
        field="specs.poles",
        property_source=f"properties.{PROPERTY_KEYS['poles']}",
        property_value=property_text(properties, PROPERTY_KEYS["poles"]),
        name=name,
        description=description,
        parser=parse_poles,
    )
    if warning:
        warnings.append(warning)
    current, warning = _resolve_measure(
        field="specs.nominal_current_a",
        property_source=f"properties.{PROPERTY_KEYS['current']}",
        property_value=property_text(properties, PROPERTY_KEYS["current"]),
        name=name,
        description=description,
        parser=parse_current,
    )
    if warning:
        warnings.append(warning)
    breaking, warning = _resolve_measure(
        field="specs.breaking_capacity_ka",
        property_source=f"properties.{PROPERTY_KEYS['breaking']}",
        property_value=property_text(properties, PROPERTY_KEYS["breaking"]),
        name=name,
        description=description,
        parser=parse_breaking_capacity,
    )
    if warning:
        warnings.append(warning)
    voltage, warning = _resolve_measure(
        field="specs.nominal_voltage_v",
        property_source=f"properties.{PROPERTY_KEYS['voltage']}",
        property_value=property_text(properties, PROPERTY_KEYS["voltage"]),
        name=name,
        description=description,
        parser=parse_voltage,
    )
    if warning:
        warnings.append(warning)

    offers = payload.get("offers") if isinstance(payload.get("offers"), list) else []
    stores = _normalize_stores(payload.get("stores"))
    quantity = _integer(payload.get("quantity"))
    if quantity is None and stores:
        quantity = sum(store["quantity"] for store in stores)

    normalized = {
        "id": product_id,
        "article": _text(payload.get("article")),
        "supplier_article": property_text(
            properties, PROPERTY_KEYS["supplier_article"]
        ),
        "barcode": property_text(properties, PROPERTY_KEYS["barcode"]),
        "name": name,
        "description": description,
        "brand": property_text(properties, PROPERTY_KEYS["brand"]),
        "product_type": property_text(properties, PROPERTY_KEYS["product_type"]),
        "poles": poles,
        "nominal_current_a": _normal_number(float(current)) if current is not None else None,
        "breaking_capacity_ka": _normal_number(float(breaking)) if breaking is not None else None,
        "nominal_voltage_v": _normal_number(float(voltage)) if voltage is not None else None,
        "installation_type": property_text(
            properties, PROPERTY_KEYS["installation"]
        ),
        "price_amount": _price(payload.get("price")),
        "quantity_total": quantity,
        "stores": stores,
        "offers": offers,
        "image_url": _text(payload.get("image")),
        "product_url": _text(payload.get("url")),
        "properties_raw": properties,
        "raw_payload": payload,
        "has_conflicts": bool(warnings),
        "warnings": warnings,
    }
    normalized["search_text"] = " ".join(
        str(value)
        for value in (
            normalized["article"],
            normalized["supplier_article"],
            normalized["barcode"],
            normalized["name"],
            normalized["description"],
            normalized["brand"],
            normalized["product_type"],
            normalized["poles"],
            normalized["nominal_current_a"],
            normalized["breaking_capacity_ka"],
            normalized["nominal_voltage_v"],
            normalized["installation_type"],
        )
        if value is not None
    )
    return normalized

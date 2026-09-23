from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SearchFilters(StrictModel):
    brand: str | None = None
    product_type: str | None = None
    supplier_article: str | None = None
    barcode: str | None = None
    poles: int | None = Field(default=None, ge=1)
    nominal_current_a: float | None = Field(default=None, ge=0)
    breaking_capacity_ka: float | None = Field(default=None, ge=0)
    nominal_voltage_v: float | None = Field(default=None, ge=0)
    in_stock: bool | None = None


class SearchRequest(StrictModel):
    query: str = Field(min_length=1, max_length=500)
    limit: int = Field(default=5, ge=1, le=20)
    filters: SearchFilters = Field(default_factory=SearchFilters)

    @field_validator("query")
    @classmethod
    def query_is_not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("query must not be blank")
        return value


class AnalogRequest(StrictModel):
    limit: int = Field(default=5, ge=1, le=20)
    require_in_stock: bool = False


class SyncRequest(StrictModel):
    enrich_details: bool = True
    max_pages: int | None = Field(default=None, ge=1)


class Store(BaseModel):
    id: int
    name: str
    quantity: int


class Specs(BaseModel):
    poles: int | None
    nominal_current_a: int | float | None
    breaking_capacity_ka: int | float | None
    nominal_voltage_v: int | float | None
    installation_type: str | None


class Price(BaseModel):
    amount: int | None
    currency: str = "KZT"
    status: Literal["live", "cached", "unknown"]
    verified_at: str | None = None


class Availability(BaseModel):
    status: Literal["live", "cached", "unknown"]
    quantity_total: int | None
    verified_at: str | None = None
    stores: list[Store] = Field(default_factory=list)


class Certificates(BaseModel):
    status: Literal["verified", "none", "unknown"] = "unknown"
    items: list[Any] = Field(default_factory=list)


class WarningValue(BaseModel):
    source: str
    value: str


class DataWarning(BaseModel):
    code: str
    field: str
    severity: Literal["warning"] = "warning"
    values: list[WarningValue] = Field(default_factory=list)


class DataQuality(BaseModel):
    has_conflicts: bool
    warnings: list[DataWarning] = Field(default_factory=list)


class ProductView(BaseModel):
    id: int
    article: str | None
    supplier_article: str | None
    barcode: str | None
    name: str
    brand: str | None
    product_type: str | None
    description: str | None
    specs: Specs
    price: Price
    availability: Availability
    image_url: str | None
    product_url: str | None
    offers: list[Any] = Field(default_factory=list)
    certificates: Certificates = Field(default_factory=Certificates)
    data_quality: DataQuality
    properties_raw: dict[str, Any] = Field(default_factory=dict)


class SearchItem(BaseModel):
    product: ProductView
    match_score: float
    match_reasons: list[str]


class SearchResponse(BaseModel):
    query: str
    items: list[SearchItem]
    total_returned: int


class ProductResponse(BaseModel):
    product: ProductView


class AvailabilityResponse(BaseModel):
    product_id: int
    status: Literal["live"] = "live"
    quantity_total: int | None
    verified_at: str
    stores: list[Store] = Field(default_factory=list)


class DifferentField(BaseModel):
    field: str
    source_value: Any
    candidate_value: Any


class AnalogItem(BaseModel):
    product: ProductView
    compatibility_status: Literal["candidate"] = "candidate"
    score: float
    matched_fields: list[str]
    different_fields: list[DifferentField]


class AnalogResponse(BaseModel):
    source_product_id: int
    items: list[AnalogItem]


class SyncResponse(BaseModel):
    sync_id: str
    complete: bool
    pages_processed: int
    products_seen: int
    products_upserted: int
    details_enriched: int
    failed_product_ids: list[int]
    stopped_reason: str


class ErrorBody(BaseModel):
    code: str
    message: str
    request_id: str
    retryable: bool
    details: dict[str, Any] = Field(default_factory=dict)


class ErrorEnvelope(BaseModel):
    error: ErrorBody


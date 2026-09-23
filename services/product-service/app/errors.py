from typing import Any


class ServiceError(Exception):
    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        *,
        retryable: bool = False,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.retryable = retryable
        self.details = details or {}


def product_not_found(product_id: int) -> ServiceError:
    return ServiceError(
        404,
        "PRODUCT_NOT_FOUND",
        f"Product {product_id} was not found",
        details={"product_id": product_id},
    )


from typing import Any
from uuid import UUID, uuid4

from .product_client import ProductClient


TOOL_DEFINITIONS = [
    {"type": "function", "function": {"name": "search_products", "description": "Search products", "parameters": {"type": "object", "properties": {"query": {"type": "string"}, "filters": {"type": "object"}, "limit": {"type": "integer"}}, "required": ["query"]}}},
    {"type": "function", "function": {"name": "get_product", "description": "Get product details", "parameters": {"type": "object", "properties": {"product_id": {"type": "integer"}}, "required": ["product_id"]}}},
    {"type": "function", "function": {"name": "find_analogs", "description": "Find product analogs", "parameters": {"type": "object", "properties": {"product_id": {"type": "integer"}, "limit": {"type": "integer"}}, "required": ["product_id"]}}},
    {"type": "function", "function": {"name": "get_purchase_conditions", "description": "Read verified purchase conditions", "parameters": {"type": "object", "properties": {"question": {"type": "string"}}, "required": ["question"]}}},
    {"type": "function", "function": {"name": "propose_cart_add", "description": "Create a safe cart proposal", "parameters": {"type": "object", "properties": {"product_id": {"type": "integer"}, "quantity": {"type": "integer"}}, "required": ["product_id", "quantity"]}}},
]


async def execute_tool(name: str, arguments: dict[str, Any], client: ProductClient, knowledge_dir: str) -> dict[str, Any]:
    if name == "search_products":
        return await client.search_products(arguments["query"], arguments.get("filters"), arguments.get("limit", 5))
    if name == "get_product":
        return await client.get_product(int(arguments["product_id"]))
    if name == "find_analogs":
        return await client.find_analogs(int(arguments["product_id"]), arguments.get("limit", 5))
    if name == "get_purchase_conditions":
        return {"code": "KNOWLEDGE_NOT_AVAILABLE", "message": "Verified purchase conditions are not configured"}
    if name == "propose_cart_add":
        quantity = int(arguments["quantity"])
        if quantity < 1:
            raise ValueError("quantity must be >= 1")
        return {"type": "PROPOSE_CART_ADD", "proposal_id": str(uuid4()), "product_id": int(arguments["product_id"]), "quantity": quantity}
    raise ValueError(f"Unknown tool: {name}")

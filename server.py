"""
server.py — Commerce MCP Server
================================
A FastMCP server exposing a product catalog as an MCP Resource and
providing product search + checkout initiation as MCP Tools.

Transport: Streamable HTTP (deployable to Vercel)
Auth:      Optional API key via X-API-Key header

Full build guide: https://30daypivot.com/agentmall_spoke_mcp
"""

from __future__ import annotations

import json
import os
from typing import Optional

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from mcp.server.fastmcp import FastMCP
from starlette.middleware.base import BaseHTTPMiddleware

# ─────────────────────────────────────────────
# 1. Environment
# ─────────────────────────────────────────────
API_KEY = os.getenv("API_KEY", "dev-secret-key")
REQUIRE_AUTH = os.getenv("REQUIRE_AUTH", "false").lower() == "true"


# ─────────────────────────────────────────────
# 2. Product Data
#    Replace with your real database call.
# ─────────────────────────────────────────────
PRODUCTS = [
    {
        "sku": "WIDGET-001",
        "name": "Ergonomic Mesh Chair",
        "price": 349.99,
        "description": "Lumbar support, adjustable armrests, breathable mesh back. Ships in 3-5 days.",
        "availability": "in_stock",
        "category": "furniture",
        "image_url": "https://example.com/images/widget-001.jpg",
    },
    {
        "sku": "GADGET-001",
        "name": "4K Webcam Pro",
        "price": 89.99,
        "description": "2160p 30fps, built-in microphone, auto light correction. USB-C + USB-A.",
        "availability": "in_stock",
        "category": "electronics",
        "image_url": "https://example.com/images/gadget-001.jpg",
    },
    {
        "sku": "GADGET-002",
        "name": "Mechanical Keyboard TKL",
        "price": 125.00,
        "description": "Tenkeyless layout, Cherry MX Blue switches, PBT keycaps, USB-C detachable cable.",
        "availability": "low_stock",
        "category": "electronics",
        "image_url": "https://example.com/images/gadget-002.jpg",
    },
    {
        "sku": "SUPPLY-001",
        "name": "Cable Management Kit (50pc)",
        "price": 19.99,
        "description": "Velcro ties, cable sleeves, adhesive clips. Compatible with most desk setups.",
        "availability": "in_stock",
        "category": "accessories",
        "image_url": "https://example.com/images/supply-001.jpg",
    },
]


# ─────────────────────────────────────────────
# 3. FastMCP Server
#
#    stateless_http=True is REQUIRED for Vercel.
#    Each request is independent; no session state
#    held between requests. Compatible with all
#    standard MCP clients.
# ─────────────────────────────────────────────
mcp = FastMCP(
    "Commerce Catalog Server",
    stateless_http=True,
)


# ─────────────────────────────────────────────
# 4. Resource: Product Catalog
# ─────────────────────────────────────────────
@mcp.resource(
    "products://catalog",
    name="Product Catalog",
    description=(
        "Full product catalog. SKU, name, price, description, "
        "availability, category, image_url for every product."
    ),
    mime_type="application/json",
)
def get_product_catalog() -> str:
    """Returns the complete product catalog as a JSON string."""
    return json.dumps(PRODUCTS, indent=2)


# ─────────────────────────────────────────────
# 5. Tool: Search Products
# ─────────────────────────────────────────────
@mcp.tool()
def search_products(
    keyword: str,
    category: Optional[str] = None,
    max_price: Optional[float] = None,
) -> dict:
    """
    Search the product catalog by keyword. Optionally filter by category
    and/or a maximum price in USD.

    Args:
        keyword:   Search term, matched against name and description.
        category:  Optional filter. Valid: furniture, electronics, accessories.
        max_price: Optional maximum price in USD (inclusive).

    Returns:
        Dict with 'count' (int) and 'results' (list of matching products).
    """
    kw = keyword.lower()
    results = []
    for product in PRODUCTS:
        if kw not in product["name"].lower() and kw not in product["description"].lower():
            continue
        if category and product["category"].lower() != category.lower():
            continue
        if max_price is not None and product["price"] > max_price:
            continue
        results.append(product)

    return {
        "count": len(results),
        "query": {"keyword": keyword, "category": category, "max_price": max_price},
        "results": results,
    }


# ─────────────────────────────────────────────
# 6. Tool: Initiate Checkout
# ─────────────────────────────────────────────
@mcp.tool()
def initiate_checkout(sku: str, quantity: int) -> dict:
    """
    Initiate a checkout session for a SKU + quantity.

    Args:
        sku:      Product SKU from search_products results.
        quantity: Integer >= 1.

    Returns:
        On success: dict with success=True, order_id, checkout_url, summary.
        On failure: dict with success=False, error message.
    """
    if quantity < 1:
        return {"success": False, "error": "Quantity must be at least 1."}

    product = next((p for p in PRODUCTS if p["sku"].upper() == sku.upper()), None)
    if product is None:
        return {
            "success": False,
            "error": f"SKU '{sku}' not found. Use search_products to find valid SKUs.",
        }
    if product["availability"] not in ("in_stock", "low_stock"):
        return {
            "success": False,
            "error": f"Product '{product['name']}' is currently {product['availability']}.",
        }

    total = round(product["price"] * quantity, 2)
    order_id = f"ORD-{sku.upper()}-{quantity:03d}"

    # Production: replace with stripe.checkout.Session.create(...)
    return {
        "success": True,
        "order_id": order_id,
        "sku": product["sku"],
        "product_name": product["name"],
        "quantity": quantity,
        "unit_price": product["price"],
        "total_usd": total,
        "checkout_url": f"https://checkout.example.com/session/{order_id}",
        "summary": (
            f"Order {order_id}: {quantity}x {product['name']} "
            f"@ ${product['price']:.2f} = ${total:.2f} total."
        ),
    }


# ─────────────────────────────────────────────
# 7. Optional API-key middleware
# ─────────────────────────────────────────────
class ApiKeyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path.startswith("/mcp"):
            provided = request.headers.get("X-API-Key", "")
            if REQUIRE_AUTH and provided != API_KEY:
                return JSONResponse(
                    status_code=401,
                    content={"error": "Unauthorized. Provide a valid X-API-Key header."},
                )
        return await call_next(request)


# ─────────────────────────────────────────────
# 8. FastAPI app — CORS, middleware, health, mount
# ─────────────────────────────────────────────
app = FastAPI(
    title="Commerce MCP Server",
    description="MCP server exposing product catalog, search, and checkout.",
    version="1.0.0",
)

# CORS — wide open for development. Restrict allow_origins in production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
    expose_headers=["Mcp-Session-Id"],
)

app.add_middleware(ApiKeyMiddleware)


@app.get("/health")
async def health_check():
    return {"status": "ok", "server": "Commerce MCP Server", "version": "1.0.0"}


# Mount the FastMCP Streamable HTTP app at /mcp
app.mount("/mcp", mcp.streamable_http_app())


# ─────────────────────────────────────────────
# 9. Local run
# ─────────────────────────────────────────────
if __name__ == "__main__":
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )

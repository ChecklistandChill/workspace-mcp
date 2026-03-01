"""
Gumroad MCP Tools

This module provides MCP tools for interacting with the Gumroad API
to manage products in your Gumroad store.
"""

import logging
import os
from typing import Optional

import httpx

from core.server import server

logger = logging.getLogger(__name__)

GUMROAD_API_BASE = "https://api.gumroad.com/v2"


def _get_access_token() -> str:
    token = os.environ.get("GUMROAD_ACCESS_TOKEN")
    if not token:
        raise ValueError(
            "GUMROAD_ACCESS_TOKEN environment variable not set. "
            "Please set it to your Gumroad API access token."
        )
    return token


@server.tool()
async def list_products() -> str:
    """
    List all products in your Gumroad store.

    Returns:
        str: Formatted list of all products including name, ID, price, URL, and status.
    """
    access_token = _get_access_token()
    logger.info("[list_products] Fetching all Gumroad products")

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{GUMROAD_API_BASE}/products",
            params={"access_token": access_token},
        )
        response.raise_for_status()
        data = response.json()

    if not data.get("success"):
        raise Exception(f"Gumroad API error: {data.get('message', 'Unknown error')}")

    products = data.get("products", [])

    if not products:
        return "No products found in your Gumroad store."

    result = f"Found {len(products)} product(s) in your Gumroad store:\n\n"
    for i, product in enumerate(products, 1):
        price_cents = product.get("price", 0)
        price_display = f"${price_cents / 100:.2f}" if price_cents else "Free"
        result += f"{i}. {product.get('name', 'Untitled')}\n"
        result += f"   ID: {product.get('id', 'N/A')}\n"
        result += f"   Price: {price_display}\n"
        result += f"   URL: {product.get('short_url', product.get('url', 'N/A'))}\n"
        result += f"   Published: {product.get('published', False)}\n"
        result += f"   Sales count: {product.get('sales_count', 0)}\n"
        result += f"   Sales revenue: ${product.get('sales_usd_cents', 0) / 100:.2f}\n"
        result += "\n"

    logger.info(f"[list_products] Successfully retrieved {len(products)} products")
    return result


@server.tool()
async def get_product(product_id: str) -> str:
    """
    Get details of a single Gumroad product by its ID.

    Args:
        product_id: The unique identifier of the product.

    Returns:
        str: Formatted product details.
    """
    access_token = _get_access_token()
    logger.info(f"[get_product] Fetching product: {product_id}")

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{GUMROAD_API_BASE}/products/{product_id}",
            params={"access_token": access_token},
        )
        response.raise_for_status()
        data = response.json()

    if not data.get("success"):
        raise Exception(f"Gumroad API error: {data.get('message', 'Unknown error')}")

    product = data.get("product", {})
    price_cents = product.get("price", 0)
    price_display = f"${price_cents / 100:.2f}" if price_cents else "Free"

    result = f"Product Details:\n\n"
    result += f"Name: {product.get('name', 'Untitled')}\n"
    result += f"ID: {product.get('id', 'N/A')}\n"
    result += f"Description: {product.get('description', 'No description')}\n"
    result += f"Price: {price_display}\n"
    result += f"Currency: {product.get('currency', 'usd')}\n"
    result += f"URL: {product.get('short_url', product.get('url', 'N/A'))}\n"
    result += f"Published: {product.get('published', False)}\n"
    result += f"Customizable price: {product.get('customizable_price', False)}\n"
    result += f"Sales count: {product.get('sales_count', 0)}\n"
    result += f"Sales revenue: ${product.get('sales_usd_cents', 0) / 100:.2f}\n"

    if product.get("variants"):
        result += f"Variants: {len(product['variants'])}\n"

    logger.info(f"[get_product] Successfully retrieved product: {product_id}")
    return result


@server.tool()
async def create_product(
    name: str,
    price: int,
    description: Optional[str] = None,
    url: Optional[str] = None,
) -> str:
    """
    Create a new product in your Gumroad store.

    Args:
        name: The name of the product.
        price: Price in cents (e.g., 500 = $5.00). Use 0 for free products.
        description: Optional product description.
        url: Optional custom URL slug for the product.

    Returns:
        str: Confirmation with the new product's details.
    """
    access_token = _get_access_token()
    logger.info(f"[create_product] Creating product: {name}")

    form_data = {
        "access_token": access_token,
        "name": name,
        "price": str(price),
    }
    if description:
        form_data["description"] = description
    if url:
        form_data["url"] = url

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{GUMROAD_API_BASE}/products",
            data=form_data,
        )
        response.raise_for_status()
        data = response.json()

    if not data.get("success"):
        raise Exception(f"Gumroad API error: {data.get('message', 'Unknown error')}")

    product = data.get("product", {})
    price_cents = product.get("price", 0)
    price_display = f"${price_cents / 100:.2f}" if price_cents else "Free"

    result = f"Product created successfully!\n\n"
    result += f"Name: {product.get('name', name)}\n"
    result += f"ID: {product.get('id', 'N/A')}\n"
    result += f"Price: {price_display}\n"
    result += f"URL: {product.get('short_url', product.get('url', 'N/A'))}\n"
    result += f"Published: {product.get('published', False)}\n"

    logger.info(f"[create_product] Successfully created product: {product.get('id')}")
    return result


@server.tool()
async def update_product(
    product_id: str,
    name: Optional[str] = None,
    description: Optional[str] = None,
    price: Optional[int] = None,
) -> str:
    """
    Update an existing Gumroad product.

    Args:
        product_id: The unique identifier of the product to update.
        name: New name for the product.
        description: New description for the product.
        price: New price in cents (e.g., 500 = $5.00).

    Returns:
        str: Confirmation with the updated product details.
    """
    access_token = _get_access_token()
    logger.info(f"[update_product] Updating product: {product_id}")

    form_data = {"access_token": access_token}
    if name is not None:
        form_data["name"] = name
    if description is not None:
        form_data["description"] = description
    if price is not None:
        form_data["price"] = str(price)

    if len(form_data) == 1:
        return "No fields to update. Provide at least one of: name, description, or price."

    async with httpx.AsyncClient() as client:
        response = await client.put(
            f"{GUMROAD_API_BASE}/products/{product_id}",
            data=form_data,
        )
        response.raise_for_status()
        data = response.json()

    if not data.get("success"):
        raise Exception(f"Gumroad API error: {data.get('message', 'Unknown error')}")

    product = data.get("product", {})
    price_cents = product.get("price", 0)
    price_display = f"${price_cents / 100:.2f}" if price_cents else "Free"

    result = f"Product updated successfully!\n\n"
    result += f"Name: {product.get('name', 'Untitled')}\n"
    result += f"ID: {product.get('id', product_id)}\n"
    result += f"Description: {product.get('description', 'No description')}\n"
    result += f"Price: {price_display}\n"
    result += f"URL: {product.get('short_url', product.get('url', 'N/A'))}\n"

    logger.info(f"[update_product] Successfully updated product: {product_id}")
    return result


@server.tool()
async def delete_product(product_id: str) -> str:
    """
    Delete a product from your Gumroad store.

    Args:
        product_id: The unique identifier of the product to delete.

    Returns:
        str: Confirmation that the product was deleted.
    """
    access_token = _get_access_token()
    logger.info(f"[delete_product] Deleting product: {product_id}")

    async with httpx.AsyncClient() as client:
        response = await client.delete(
            f"{GUMROAD_API_BASE}/products/{product_id}",
            params={"access_token": access_token},
        )
        response.raise_for_status()
        data = response.json()

    if not data.get("success"):
        raise Exception(f"Gumroad API error: {data.get('message', 'Unknown error')}")

    result = f"Product '{product_id}' has been successfully deleted."

    logger.info(f"[delete_product] Successfully deleted product: {product_id}")
    return result

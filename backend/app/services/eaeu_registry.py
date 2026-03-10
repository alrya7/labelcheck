import logging
from urllib.parse import quote

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

BASE_URL = settings.eaeu_api_base_url
DICT_CODE = settings.eaeu_sgr_dict_code


async def search_by_number(numb_doc: str) -> dict | None:
    """Search for an SGR record by document number in the EAEU registry."""
    url = (
        f"{BASE_URL}/dictionaries/{DICT_CODE}/elements"
        f"?conditions[0].conditionType=like"
        f"&conditions[0].code=NUMB_DOC"
        f"&conditions[0].value={quote(numb_doc)}"
        f"&offset=0&limit=10"
    )

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        data = resp.json()

    elements = data.get("elements", [])
    if not elements:
        return None

    # Find exact match
    for el in elements:
        if el.get("data", {}).get("NUMB_DOC") == numb_doc:
            return el

    # Return first result if no exact match
    return elements[0]


async def search_by_manufacturer(name: str, limit: int = 50) -> list[dict]:
    """Search for SGR records by manufacturer name."""
    url = (
        f"{BASE_URL}/dictionaries/{DICT_CODE}/elements"
        f"?conditions[0].conditionType=like"
        f"&conditions[0].code=FIRMGET_NAME"
        f"&conditions[0].value={quote(name)}"
        f"&offset=0&limit={limit}"
    )

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        data = resp.json()

    return data.get("elements", [])


async def get_sgr_status(numb_doc: str) -> str | None:
    """Get the current status of an SGR by document number."""
    record = await search_by_number(numb_doc)
    if not record:
        return None
    return record.get("data", {}).get("STATUS", {}).get("name")


async def get_full_record(numb_doc: str) -> dict | None:
    """Get the full EAEU registry record for an SGR number."""
    return await search_by_number(numb_doc)


async def search_product(product_name: str, limit: int = 20) -> list[dict]:
    """Search for SGR records by product name."""
    url = (
        f"{BASE_URL}/dictionaries/{DICT_CODE}/elements"
        f"?conditions[0].conditionType=like"
        f"&conditions[0].code=NAME_PROD"
        f"&conditions[0].value={quote(product_name)}"
        f"&offset=0&limit={limit}"
    )

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        data = resp.json()

    return data.get("elements", [])

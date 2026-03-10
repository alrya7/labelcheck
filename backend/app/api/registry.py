from fastapi import APIRouter

from app.services import eaeu_registry

router = APIRouter(prefix="/registry", tags=["EAEU Registry"])


@router.get("/search")
async def search_registry(
    numb_doc: str | None = None,
    manufacturer: str | None = None,
    product: str | None = None,
    limit: int = 20,
):
    """Search the EAEU SGR registry."""
    if numb_doc:
        record = await eaeu_registry.search_by_number(numb_doc)
        return {"results": [record] if record else [], "total": 1 if record else 0}

    if manufacturer:
        records = await eaeu_registry.search_by_manufacturer(manufacturer, limit)
        return {"results": records, "total": len(records)}

    if product:
        records = await eaeu_registry.search_product(product, limit)
        return {"results": records, "total": len(records)}

    return {"error": "Укажите хотя бы один параметр поиска: numb_doc, manufacturer или product"}

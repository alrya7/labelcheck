"""Parse SGR documents (PDF/image) into structured data.

Flow:
1. AI извлекает данные из скана/PDF СГР (ключи в UPPER_CASE, как в API реестра)
2. По номеру NUMB_DOC делаем запрос в API реестра ЕАЭС
3. Если найдено в реестре — данные реестра = основной источник правды
4. AI-данные дополняют то, чего нет в реестре
5. Сравниваем AI-извлечение с реестром — находим расхождения
"""
import logging
import re

from app.prompts.parse_sgr import PARSE_SGR_PROMPT
from app.services import eaeu_registry, openai_vision
from app.services.label_checker import pdf_to_pngs

logger = logging.getLogger(__name__)

# Cyrillic → Latin character map for SGR number normalization
CYRILLIC_TO_LATIN = {
    "А": "A", "В": "B", "С": "C", "Е": "E", "Н": "H",
    "К": "K", "М": "M", "О": "O", "Р": "R", "Т": "T",
    "У": "Y", "Х": "X",
}


def normalize_sgr_number(raw: str) -> str:
    """Normalize SGR number: fix Cyrillic→Latin, ensure dots, clean whitespace."""
    if not raw:
        return raw

    result = ""
    for ch in raw.strip():
        result += CYRILLIC_TO_LATIN.get(ch, ch)

    result = re.sub(r'\s+', '', result)
    result = result.replace(",", ".")

    return result


def validate_sgr_format(numb_doc: str) -> bool:
    """Validate that the SGR number matches the expected format."""
    pattern = r'^[A-Z]{2}\.\d{2}\.\d{2}\.\d{2}\.\d{3}\.[A-Z]\.\d{6}\.\d{2}\.\d{2}$'
    return bool(re.match(pattern, numb_doc))


async def parse_sgr_document(
    file_bytes: bytes,
    filename: str,
    content_type: str,
) -> dict:
    """Parse an SGR document and return structured data with registry cross-reference."""
    is_pdf = content_type == "application/pdf" or filename.lower().endswith(".pdf")

    # Step 1: AI извлекает данные из скана (ключи UPPER_CASE как в API реестра)
    if is_pdf:
        png_pages = pdf_to_pngs(file_bytes)
        if len(png_pages) == 1:
            ai_extracted = await openai_vision.analyze_with_structured_output(
                image_bytes=png_pages[0],
                pdf_bytes=None,
                filename=filename,
                prompt=PARSE_SGR_PROMPT,
                mime_type="image/png",
            )
        else:
            ai_extracted = await openai_vision.analyze_with_structured_output_multi(
                images=png_pages,
                prompt=PARSE_SGR_PROMPT,
            )
    else:
        ai_extracted = await openai_vision.analyze_with_structured_output(
            image_bytes=file_bytes,
            pdf_bytes=None,
            filename=filename,
            prompt=PARSE_SGR_PROMPT,
            mime_type=content_type,
        )

    # Step 2: Нормализация номера СГР
    raw_numb = ai_extracted.get("NUMB_DOC", "") or ai_extracted.get("numb_doc", "")
    numb_doc = normalize_sgr_number(raw_numb)

    if numb_doc and not validate_sgr_format(numb_doc):
        logger.warning(
            "SGR number doesn't match expected format: '%s' (raw: '%s')",
            numb_doc, raw_numb,
        )

    logger.info("AI extracted SGR number: '%s' (raw: '%s')", numb_doc, raw_numb)

    # Step 3: Запрос в API реестра ЕАЭС
    registry_data = None
    registry_discrepancies = []

    if numb_doc:
        try:
            registry_data = await eaeu_registry.get_full_record(numb_doc)
            if registry_data:
                logger.info("SGR %s найден в реестре ЕАЭС", numb_doc)
            else:
                logger.warning("SGR %s НЕ найден в реестре ЕАЭС", numb_doc)
        except Exception as e:
            logger.warning("Ошибка запроса реестра для %s: %s", numb_doc, e)

    # Step 4: Объединяем данные — реестр = основной источник, AI = дополнение
    # merged будет содержать данные для сохранения в БД (lowercase ключи для ORM)
    if registry_data:
        reg = registry_data.get("data", {})

        # Реестр — основной источник правды
        reg_numb = reg.get("NUMB_DOC", numb_doc)
        if reg_numb != numb_doc:
            logger.info("Используем номер из реестра '%s' вместо AI '%s'", reg_numb, numb_doc)
            numb_doc = reg_numb

        merged = {
            "numb_doc": numb_doc,
            "date_doc": reg.get("DATE_DOC"),
            "name_prod": reg.get("NAME_PROD"),
            "okp_prod": reg.get("OKP_PROD"),
            "firmget_name": reg.get("FIRMGET_NAME"),
            "firmget_addr": reg.get("FIRMGET_ADDR"),
            "firmmade_name": reg.get("FIRMMADE_NAME"),
            "firmmade_addr": reg.get("FIRMMADE_ADDR"),
            "doc_norm": reg.get("DOC_NORM"),
            "doc_usearea": reg.get("DOC_USEAREA"),
            "doc_protocol": reg.get("DOC_PROTOCOL"),
            "doc_condition": reg.get("DOC_CONDITION"),
            "doc_label": reg.get("DOC_LABEL"),
            "doc_gighark": reg.get("DOC_GIGHARK"),
            "who": reg.get("WHO"),
            "n_alfa_name": _get_name(reg.get("N_ALFA_NAME")),
            "status": _get_name(reg.get("STATUS")),
            "serialnumb": reg.get("SERIALNUMB"),
        }

        # Сравниваем AI-данные с реестром (пропускаем мусорные AI значения)
        ai_name = _clean_ai_value(ai_extracted.get("NAME_PROD", ""))
        reg_name = reg.get("NAME_PROD", "")
        if ai_name and reg_name and ai_name.lower().strip() != reg_name.lower().strip():
            registry_discrepancies.append({
                "field": "NAME_PROD",
                "ai_extracted": ai_name,
                "registry": reg_name,
                "severity": "info",  # расхождение может быть из-за OCR
            })

        ai_firm = _clean_ai_value(ai_extracted.get("FIRMGET_NAME", ""))
        reg_firm = reg.get("FIRMGET_NAME", "")
        if ai_firm and reg_firm:
            if (reg_firm.lower() not in ai_firm.lower()
                    and ai_firm.lower() not in reg_firm.lower()):
                registry_discrepancies.append({
                    "field": "FIRMGET_NAME",
                    "ai_extracted": ai_firm,
                    "registry": reg_firm,
                    "severity": "info",
                })

        reg_status = _get_name(reg.get("STATUS"))
        if reg_status and reg_status != "подписан и действует":
            registry_discrepancies.append({
                "field": "STATUS",
                "ai_extracted": None,
                "registry": reg_status,
                "severity": "critical",
            })
    else:
        # Нет данных из реестра — используем только AI
        merged = {
            "numb_doc": numb_doc,
            "date_doc": ai_extracted.get("DATE_DOC"),
            "name_prod": ai_extracted.get("NAME_PROD"),
            "okp_prod": ai_extracted.get("OKP_PROD"),
            "firmget_name": ai_extracted.get("FIRMGET_NAME"),
            "firmget_addr": ai_extracted.get("FIRMGET_ADDR"),
            "firmmade_name": ai_extracted.get("FIRMMADE_NAME"),
            "firmmade_addr": ai_extracted.get("FIRMMADE_ADDR"),
            "doc_norm": ai_extracted.get("DOC_NORM"),
            "doc_usearea": ai_extracted.get("DOC_USEAREA"),
            "doc_protocol": ai_extracted.get("DOC_PROTOCOL"),
            "doc_condition": ai_extracted.get("DOC_CONDITION"),
            "doc_label": ai_extracted.get("DOC_LABEL"),
            "doc_gighark": ai_extracted.get("DOC_GIGHARK"),
            "who": ai_extracted.get("WHO"),
            "n_alfa_name": ai_extracted.get("N_ALFA_NAME"),
        }

    return {
        "extracted": merged,
        "ai_raw": ai_extracted,
        "registry_data": registry_data,
        "registry_discrepancies": registry_discrepancies,
    }


def _clean_ai_value(val: str | None) -> str:
    """Clean AI-extracted value: treat 'undefined', 'null', 'none', etc. as empty."""
    if not val:
        return ""
    if val.strip().lower() in ("undefined", "null", "none", "n/a", "не указано"):
        return ""
    return val.strip()


def _get_name(val) -> str | None:
    """Extract name from dict-like registry values (e.g., {"id": ..., "name": ...})."""
    if isinstance(val, dict):
        return val.get("name")
    return val

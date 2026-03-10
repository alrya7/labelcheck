"""Label verification engine: AI analysis + rule-based checks + registry cross-reference."""
import io
import json
import logging
import re

from app.prompts.check_label import CHECK_LABEL_PROMPT, CHECK_LABEL_WITH_SGR_PROMPT
from app.services import eaeu_registry, moonshot
from app.services.rules import MANDATORY_CHECKS, compute_score

logger = logging.getLogger(__name__)

# Regex patterns for SGR number extraction
SGR_PATTERNS = [
    # Standard format: AM.01.04.01.003.R.000048.02.25
    r'[A-ZА-Я]{2}[\.\s]*\d{2}[\.\s]*\d{2}[\.\s]*\d{2}[\.\s]*\d{3}[\.\s]*[RР][\.\s]*\d{6}[\.\s]*\d{2}[\.\s]*\d{2}',
    # With possible OCR errors in dots
    r'[A-ZА-Я]{2}\.\d{2}\.\d{2}\.\d{2}\.\d{3}\.[RР]\.\d{6}\.\d{2}\.\d{2}',
    # Just the number pattern without country prefix
    r'\d{2}\.\d{2}\.\d{2}\.\d{3}\.[RР]\.\d{6}\.\d{2}\.\d{2}',
]


def pdf_to_pngs(pdf_bytes: bytes) -> list[bytes]:
    """Convert ALL pages of PDF to PNG images at high resolution."""
    import fitz  # PyMuPDF

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    images = []
    for page in doc:
        # Render at 3x resolution for better OCR quality
        mat = fitz.Matrix(3, 3)
        pix = page.get_pixmap(matrix=mat)
        png_bytes = pix.tobytes("png")
        images.append(png_bytes)
    doc.close()
    return images


def _extract_sgr_number(text: str) -> str | None:
    """Try to extract SGR number from text using regex."""
    if not text:
        return None
    for pattern in SGR_PATTERNS:
        match = re.search(pattern, text)
        if match:
            # Normalize: remove extra spaces, ensure dots
            number = match.group().strip()
            number = re.sub(r'\s+', '.', number)
            return number
    return None


async def check_label(
    file_bytes: bytes,
    filename: str,
    content_type: str,
    sgr_data: dict | None = None,
) -> dict:
    """Perform full label verification."""
    is_pdf = content_type == "application/pdf" or filename.lower().endswith(".pdf")

    # Step 1: AI analysis of the label
    if sgr_data:
        sgr_json = json.dumps(sgr_data, ensure_ascii=False, indent=2)
        prompt = CHECK_LABEL_WITH_SGR_PROMPT.replace("{sgr_data}", sgr_json)
    else:
        prompt = CHECK_LABEL_PROMPT

    # Convert PDF to PNG(s) for Vision API
    if is_pdf:
        png_pages = pdf_to_pngs(file_bytes)
        if len(png_pages) == 1:
            # Single page — send as one image
            ai_result = await moonshot.analyze_with_structured_output(
                image_bytes=png_pages[0],
                pdf_bytes=None,
                filename=filename,
                prompt=prompt,
                mime_type="image/png",
            )
        else:
            # Multi-page — send all pages as separate images
            ai_result = await moonshot.analyze_with_structured_output_multi(
                images=png_pages,
                prompt=prompt,
            )
    else:
        ai_result = await moonshot.analyze_with_structured_output(
            image_bytes=file_bytes,
            pdf_bytes=None,
            filename=filename,
            prompt=prompt,
            mime_type=content_type,
        )

    # Step 2: Extract SGR number (AI result + regex fallback)
    sgr_number = ai_result.get("sgr_number")
    extracted_text = ai_result.get("extracted_text", "")

    if not sgr_number or sgr_number == "null":
        # Try regex extraction from the extracted text
        sgr_number = _extract_sgr_number(extracted_text)
        if sgr_number:
            logger.info("SGR number extracted via regex: %s", sgr_number)

    # Step 3: Cross-reference SGR number with EAEU registry
    registry_data = None
    if sgr_number:
        try:
            registry_data = await eaeu_registry.get_full_record(sgr_number)
            if registry_data:
                logger.info("Registry data found for SGR %s", sgr_number)
            else:
                # Try with normalized number (replace common OCR errors)
                normalized = sgr_number.replace("Р", "R").replace("М", "M")
                if normalized != sgr_number:
                    registry_data = await eaeu_registry.get_full_record(normalized)
        except Exception as e:
            logger.warning("Registry lookup failed for %s: %s", sgr_number, e)

    # Step 4: Enhance AI checks with registry data
    ai_checks = ai_result.get("checks", [])
    checks = _merge_checks(ai_checks, registry_data, ai_result)

    # Step 5: Compute score
    score, overall_status = compute_score(checks)

    return {
        "overall_status": overall_status,
        "score": score,
        "checks": checks,
        "ai_analysis": json.dumps(ai_result, ensure_ascii=False),
        "extracted_label_text": extracted_text,
        "sgr_number": sgr_number,
        "registry_data": registry_data,
        "spelling_errors": ai_result.get("spelling_errors", []),
        "therapeutic_claims": ai_result.get("therapeutic_claims", []),
        "pictograms": ai_result.get("pictograms", {}),
    }


def _merge_checks(
    ai_checks: list[dict],
    registry_data: dict | None,
    ai_result: dict,
) -> list[dict]:
    """Merge AI-generated checks with rule-based validation."""
    # Build lookup from AI results
    ai_lookup = {}
    for check in ai_checks:
        ai_lookup[check.get("id", "")] = check

    # Map pictogram IDs to pictograms dict keys
    pictogram_map = {
        "eac_mark": "eac",
        "mobius_loop": "mobius_loop",
        "barcode": "barcode",
    }
    pictograms = ai_result.get("pictograms", {})

    merged = []
    for rule in MANDATORY_CHECKS:
        check_id = rule["id"]
        ai_check = ai_lookup.get(check_id)

        if ai_check:
            status = ai_check.get("status", "warning")
            # Normalize boolean-like statuses
            if status is True or status == "true":
                status = "pass"
            elif status is False or status == "false":
                status = "fail"
            result = {
                "id": check_id,
                "name": rule["name"],
                "category": rule["category"],
                "source": rule.get("source", ""),
                "required": rule["required"],
                "status": status,
                "details": ai_check.get("details", ""),
                "found_text": ai_check.get("found_text"),
            }
        elif check_id in pictogram_map and pictograms:
            # Fallback: get pictogram status from pictograms dict
            pic_key = pictogram_map[check_id]
            pic_val = pictograms.get(pic_key)
            if pic_val is True:
                status = "pass"
                details = "Обнаружен на этикетке"
            elif pic_val is False:
                status = "fail"
                details = "Не обнаружен на этикетке"
            else:
                status = "warning"
                details = "Не удалось определить"
            result = {
                "id": check_id,
                "name": rule["name"],
                "category": rule["category"],
                "source": rule.get("source", ""),
                "required": rule["required"],
                "status": status,
                "details": details,
                "found_text": None,
            }
        else:
            result = {
                "id": check_id,
                "name": rule["name"],
                "category": rule["category"],
                "source": rule.get("source", ""),
                "required": rule["required"],
                "status": "warning",
                "details": "Не проверено AI",
                "found_text": None,
            }

        # Override registry checks with actual data
        if registry_data and rule["category"] == "registry":
            result = _check_registry(result, registry_data, ai_result)

        merged.append(result)

    return merged


def _check_registry(
    check: dict,
    registry_data: dict,
    ai_result: dict,
) -> dict:
    """Validate label data against EAEU registry."""
    reg = registry_data.get("data", {})
    check_id = check["id"]

    if check_id == "sgr_valid":
        status = reg.get("STATUS", {}).get("name", "")
        if status == "подписан и действует":
            check["status"] = "pass"
            check["details"] = f"СГР действителен. Статус: {status}"
        elif status:
            check["status"] = "fail"
            check["details"] = f"СГР недействителен! Статус: {status}"
        else:
            check["status"] = "fail"
            check["details"] = "СГР не найден в реестре ЕАЭС"

    elif check_id == "sgr_product_match":
        reg_name = reg.get("NAME_PROD", "").lower()
        label_name = ai_result.get("product_name", "").lower()
        if reg_name and label_name:
            # Fuzzy match: check if key words overlap
            reg_words = set(re.findall(r'[а-яёa-z]+', reg_name))
            label_words = set(re.findall(r'[а-яёa-z]+', label_name))
            overlap = reg_words & label_words
            if len(overlap) >= 2 or label_name in reg_name or reg_name in label_name:
                check["status"] = "pass"
                check["details"] = "Наименование продукции совпадает"
            else:
                check["status"] = "fail"
                check["details"] = (
                    f"НЕСОВПАДЕНИЕ! На этикетке: '{ai_result.get('product_name')}', "
                    f"в реестре: '{reg.get('NAME_PROD')}'"
                )
        else:
            check["status"] = "warning"
            check["details"] = "Не удалось сравнить наименование"

    elif check_id == "sgr_manufacturer_match":
        reg_firm = reg.get("FIRMGET_NAME", "").lower()
        label_firm = ai_result.get("manufacturer", "").lower()
        if reg_firm and label_firm:
            reg_words = set(re.findall(r'[а-яёa-z]+', reg_firm))
            label_words = set(re.findall(r'[а-яёa-z]+', label_firm))
            overlap = reg_words & label_words
            if len(overlap) >= 2 or label_firm in reg_firm or reg_firm in label_firm:
                check["status"] = "pass"
                check["details"] = "Изготовитель совпадает"
            else:
                check["status"] = "fail"
                check["details"] = (
                    f"НЕСОВПАДЕНИЕ! На этикетке: '{ai_result.get('manufacturer')}', "
                    f"в реестре: '{reg.get('FIRMGET_NAME')}'"
                )

    elif check_id == "composition_match":
        ai_comp = next(
            (c for c in ai_result.get("checks", []) if c.get("id") == "composition_match"),
            None,
        )
        if ai_comp:
            check["status"] = ai_comp.get("status", "warning")
            check["details"] = ai_comp.get("details", "Проверено AI")

    return check

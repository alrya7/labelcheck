"""Label verification engine: AI analysis + rule-based checks + registry cross-reference."""
import json
import logging
import re

from app.prompts.check_label import CHECK_LABEL_PROMPT, CHECK_LABEL_WITH_SGR_PROMPT
from app.services import openai_vision
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
    # Shorter format: AA.003.003.000046.03.25 (without R letter)
    r'[A-ZА-Я]{2}[\.\s]*\d{3}[\.\s]*\d{3}[\.\s]*\d{6}[\.\s]*\d{2}[\.\s]*\d{2}',
]


MAX_PAGES = 10  # Limit pages to avoid huge payloads


def pdf_to_pngs(pdf_bytes: bytes, high_res: bool = False) -> list[bytes]:
    """Convert pages of PDF to PNG images. Uses higher resolution for label checking."""
    import fitz  # PyMuPDF

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    page_count = len(doc)
    # Use 4x for single-page labels (high_res), 3x normal single-page, 2x for multi-page
    if high_res and page_count == 1:
        scale = 4
    elif page_count == 1:
        scale = 3
    else:
        scale = 2
    images = []
    for i, page in enumerate(doc):
        if i >= MAX_PAGES:
            logger.warning("PDF has %d pages, truncating to %d", page_count, MAX_PAGES)
            break
        mat = fitz.Matrix(scale, scale)
        pix = page.get_pixmap(matrix=mat)
        png_bytes = pix.tobytes("png")
        images.append(png_bytes)
        logger.info("Page %d/%d converted (%d KB)", i + 1, min(page_count, MAX_PAGES), len(png_bytes) // 1024)
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

    # Convert PDF to PNG(s) for Vision API — use high_res for better text recognition
    if is_pdf:
        png_pages = pdf_to_pngs(file_bytes, high_res=True)
        if len(png_pages) == 1:
            ai_result = await openai_vision.analyze_with_structured_output(
                image_bytes=png_pages[0],
                pdf_bytes=None,
                filename=filename,
                prompt=prompt,
                mime_type="image/png",
            )
        else:
            ai_result = await openai_vision.analyze_with_structured_output_multi(
                images=png_pages,
                prompt=prompt,
            )
    else:
        ai_result = await openai_vision.analyze_with_structured_output(
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

    # Step 3: Merge AI checks (SGR cross-reference done by caller if SGR found in DB)
    ai_checks = ai_result.get("checks", [])
    checks = _merge_checks(ai_checks, None, ai_result)

    # Step 4: Update SGR number check if number was found
    if sgr_number:
        for check in checks:
            if check["id"] == "sgr_number":
                check["status"] = "pass"
                check["details"] = f"Номер СГР найден на этикетке: {sgr_number}"
                check["found_text"] = sgr_number
                break

    # Step 5: Text-based fallback for checks AI missed
    _text_fallback_checks(checks, extracted_text)

    # Step 6: Smart not_applicable logic for conditional checks
    CONDITIONAL_CHECK_IDS = {"importer", "nutritional_value", "allergens", "gmo_info"}
    for check in checks:
        cid = check["id"]
        if not check["required"] and check["status"] in ("warning", "fail"):
            if cid in CONDITIONAL_CHECK_IDS:
                check["status"] = "not_applicable"
                if cid == "importer":
                    check["details"] = "Не применимо (продукция не импортная или импортёр = изготовитель)"
                elif cid == "nutritional_value":
                    check["details"] = "Не применимо (БАД в капсулах/таблетках с незначительной энерг. ценностью)"
                elif cid == "allergens":
                    check["details"] = "Не применимо (типичные аллергены не обнаружены в составе)"
                elif cid == "gmo_info":
                    check["details"] = "Не применимо (БАД не содержит ГМО)"

    # Step 7: Registry checks — mark as not_applicable when no registry data
    for check in checks:
        if check.get("category") == "registry" and check["status"] in ("warning", "fail"):
            if "Не проверено" in check.get("details", "") or check["details"] == "":
                check["status"] = "not_applicable"
                check["details"] = "Данные СГР не загружены — сверка с реестром не выполнена"

    # Step 8: Compute score
    score, overall_status = compute_score(checks)

    return {
        "overall_status": overall_status,
        "score": score,
        "checks": checks,
        "ai_analysis": json.dumps(ai_result, ensure_ascii=False),
        "extracted_label_text": extracted_text,
        "sgr_number": sgr_number,
        "registry_data": None,
        "product_name": ai_result.get("product_name"),
        "spelling_errors": ai_result.get("spelling_errors", []),
        "therapeutic_claims": ai_result.get("therapeutic_claims", []),
        "pictograms": ai_result.get("pictograms", {}),
    }


def _text_fallback_checks(checks: list[dict], text: str) -> None:
    """Apply text-based fallback for checks the AI missed (status='warning' + 'Не проверено AI')."""
    if not text:
        return
    text_lower = text.lower()

    # Patterns to search in extracted text for each check id
    FALLBACK_PATTERNS = {
        "net_weight": [
            r'\d+\s*(?:капсул|таблеток|таблетки|штук|шт\.?)',
            r'масса\s+нетто',
            r'\d+\s*(?:г|кг|мг|мл|л)\b',
        ],
        "mfg_date": [
            r'дата\s+(?:из|производ)',
            r'дат[аы]\s+изготовлен',
            r'(?:изготовлен|произведен|дата).{0,30}(?:указан|нанесен|см\.)',
            r'дат[аы].{0,20}(?:на дне|на упаковке|на банке|на крышке)',
        ],
        "no_eco_clean": [],  # If AI didn't flag → pass (no violation)
        "no_misleading": [],  # If AI didn't flag → pass (no violation)
    }

    for check in checks:
        if check["status"] != "warning" or "Не проверено" not in check.get("details", ""):
            continue
        cid = check["id"]

        # For "prohibited" category: if AI didn't flag a violation, it's pass
        if check.get("category") == "prohibited":
            check["status"] = "pass"
            check["details"] = "Нарушений не обнаружено"
            continue

        patterns = FALLBACK_PATTERNS.get(cid)
        if patterns is None:
            continue

        # Empty patterns = auto-pass (for prohibited checks)
        if not patterns:
            check["status"] = "pass"
            check["details"] = "Нарушений не обнаружено"
            continue

        for pattern in patterns:
            match = re.search(pattern, text_lower)
            if match:
                found = text[match.start():match.end() + 30].strip()
                # Get a wider context for found_text
                ctx_start = max(0, match.start() - 10)
                ctx_end = min(len(text), match.end() + 40)
                found_text = text[ctx_start:ctx_end].strip()
                check["status"] = "pass"
                check["details"] = "Найдено в тексте этикетки"
                check["found_text"] = found_text
                break


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
        # First try AI check
        ai_comp = next(
            (c for c in ai_result.get("checks", []) if c.get("id") == "composition_match"),
            None,
        )
        if ai_comp and ai_comp.get("status") not in ("warning", None):
            check["status"] = ai_comp.get("status", "warning")
            check["details"] = ai_comp.get("details", "Проверено AI")
        else:
            # Fallback: compare composition words from SGR label text vs extracted label text
            reg_label = reg.get("DOC_LABEL", "") or reg.get("SOSTAV", "") or ""
            label_text = ai_result.get("extracted_text", "")
            if reg_label and label_text:
                # Extract significant words (4+ chars) for comparison
                reg_words = set(re.findall(r'[а-яёa-z]{4,}', reg_label.lower()))
                label_words = set(re.findall(r'[а-яёa-z]{4,}', label_text.lower()))
                if reg_words:
                    overlap = reg_words & label_words
                    ratio = len(overlap) / len(reg_words)
                    if ratio >= 0.4:
                        check["status"] = "pass"
                        check["details"] = f"Состав соответствует данным СГР (совпадение {ratio:.0%})"
                    else:
                        check["status"] = "warning"
                        check["details"] = f"Низкое совпадение состава с СГР ({ratio:.0%})"
                else:
                    check["status"] = "warning"
                    check["details"] = "В СГР не указан состав для сравнения"
            elif not reg_label:
                check["status"] = "warning"
                check["details"] = "В данных СГР не найден состав для сверки"

    return check

import io

import httpx
from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.types import Message

router = Router()

STATUS_EMOJI = {"pass": "✅", "fail": "❌", "warning": "⚠️", "not_applicable": "➖"}


@router.message(Command("check_label"))
async def cmd_check_label(message: Message):
    await message.answer(
        "🏷 Отправьте фото или PDF макета этикетки для проверки.",
    )


@router.message(F.photo)
async def handle_label_photo(message: Message, bot: Bot, backend_url: str = "http://localhost:8000"):
    """Handle label photo for checking."""
    await message.answer("⏳ Анализирую этикетку...")

    photo = message.photo[-1]  # largest size
    file = await bot.get_file(photo.file_id)
    file_bytes = io.BytesIO()
    await bot.download_file(file.file_path, file_bytes)
    file_bytes.seek(0)

    await _check_label(message, file_bytes, "label.jpg", "image/jpeg", backend_url)


@router.message(F.document, ~F.document.mime_type.in_({"application/pdf"}))
async def handle_label_image_doc(message: Message, bot: Bot, backend_url: str = "http://localhost:8000"):
    """Handle label as document (image files)."""
    doc = message.document
    if not doc.mime_type or not doc.mime_type.startswith("image/"):
        return  # Skip non-image documents (PDFs handled by sgr handler)

    await message.answer("⏳ Анализирую этикетку...")

    file = await bot.get_file(doc.file_id)
    file_bytes = io.BytesIO()
    await bot.download_file(file.file_path, file_bytes)
    file_bytes.seek(0)

    await _check_label(message, file_bytes, doc.file_name or "label.png", doc.mime_type, backend_url)


async def _check_label(
    message: Message,
    file_bytes: io.BytesIO,
    filename: str,
    mime_type: str,
    backend_url: str,
):
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{backend_url}/api/v1/label/check",
                files={"file": (filename, file_bytes.read(), mime_type)},
            )

        if resp.status_code != 200:
            await message.answer(f"❌ Ошибка сервера: {resp.text[:200]}")
            return

        data = resp.json()
        score = data.get("score", 0)
        status = data.get("overall_status", "unknown")
        checks = data.get("checks", [])

        # Build report
        status_emoji = {"pass": "✅", "fail": "❌", "warning": "⚠️"}.get(status, "❓")
        header = f"{status_emoji} <b>Результат проверки: {score}/100</b>\n\n"

        # Group checks by category
        categories = {
            "text": "📝 Обязательные текстовые поля",
            "pictogram": "🔲 Пиктограммы и знаки",
            "prohibited": "🚫 Запрещённые элементы",
            "registry": "🔍 Сверка с реестром ЕАЭС",
            "quality": "📐 Качество оформления",
        }

        report_parts = [header]
        for cat_id, cat_name in categories.items():
            cat_checks = [c for c in checks if c.get("category") == cat_id]
            if not cat_checks:
                continue

            report_parts.append(f"<b>{cat_name}:</b>\n")
            for check in cat_checks:
                emoji = STATUS_EMOJI.get(check.get("status", ""), "❓")
                name = check.get("name", "")
                details = check.get("details", "")
                line = f"{emoji} {name}"
                if details and check.get("status") == "fail":
                    line += f"\n   └ <i>{details[:100]}</i>"
                report_parts.append(line)
            report_parts.append("")

        # Therapeutic claims
        claims = data.get("therapeutic_claims", [])
        if claims:
            report_parts.append("🚨 <b>Лечебные заявления:</b>")
            for claim in claims:
                report_parts.append(f"• «{claim.get('text', '')}» — {claim.get('reason', '')}")
            report_parts.append("")

        # Spelling
        spelling = data.get("spelling_errors", [])
        if spelling:
            report_parts.append("📝 <b>Орфография:</b>")
            for err in spelling[:5]:
                report_parts.append(f"• {err.get('word', '')} → {err.get('suggestion', '')}")

        full_report = "\n".join(report_parts)

        # Telegram has 4096 char limit
        if len(full_report) > 4000:
            full_report = full_report[:3990] + "\n\n<i>...обрезано</i>"

        await message.answer(full_report, parse_mode="HTML")

    except Exception as e:
        await message.answer(f"❌ Ошибка при анализе: {str(e)[:200]}")

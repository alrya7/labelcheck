import io

import httpx
from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.types import Message

router = Router()


@router.message(Command("upload_sgr"))
async def cmd_upload_sgr(message: Message):
    await message.answer(
        "📄 Отправьте файл СГР (PDF или фото) следующим сообщением.",
    )


@router.message(F.document, F.caption.contains("сгр") | F.caption.contains("СГР"))
@router.message(F.document.mime_type.in_({"application/pdf"}))
async def handle_sgr_document(message: Message, bot: Bot, backend_url: str = "http://localhost:8000"):
    """Handle SGR document upload."""
    await message.answer("⏳ Обрабатываю СГР документ...")

    doc = message.document
    file = await bot.get_file(doc.file_id)
    file_bytes = io.BytesIO()
    await bot.download_file(file.file_path, file_bytes)
    file_bytes.seek(0)

    try:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{backend_url}/api/v1/sgr/upload",
                files={"file": (doc.file_name or "sgr.pdf", file_bytes.read(), doc.mime_type)},
            )

        if resp.status_code == 200:
            data = resp.json()
            sgr = data["sgr"]
            discrepancies = data.get("registry_discrepancies", [])

            text = (
                f"✅ <b>СГР загружен успешно!</b>\n\n"
                f"📋 <b>Номер:</b> {sgr['numb_doc']}\n"
                f"📅 <b>Дата:</b> {sgr.get('date_doc', 'н/д')}\n"
                f"📦 <b>Продукция:</b> {sgr.get('name_prod', 'н/д')}\n"
                f"🏭 <b>Изготовитель:</b> {sgr.get('firmget_name', 'н/д')}\n"
                f"📊 <b>Статус:</b> {sgr.get('status', 'н/д')}\n"
            )

            if discrepancies:
                text += "\n⚠️ <b>Расхождения с реестром:</b>\n"
                for d in discrepancies:
                    text += f"• {d['field']}: {d.get('details', d.get('registry', ''))}\n"

            await message.answer(text, parse_mode="HTML")
        elif resp.status_code == 409:
            await message.answer("⚠️ Этот СГР уже есть в базе данных.")
        else:
            await message.answer(f"❌ Ошибка: {resp.text[:200]}")

    except Exception as e:
        await message.answer(f"❌ Ошибка при обработке: {str(e)[:200]}")

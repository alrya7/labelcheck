from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        "👋 <b>LabelCheck Bot</b>\n\n"
        "Проверяю этикетки БАД на соответствие законодательству РФ/ЕАЭС.\n\n"
        "<b>Как пользоваться:</b>\n"
        "1️⃣ Отправьте фото/PDF <b>СГР</b> — я извлеку данные и сохраню в базу\n"
        "2️⃣ Отправьте фото/PDF <b>этикетки</b> — я проверю её на соответствие\n\n"
        "<b>Команды:</b>\n"
        "/check_label — проверить этикетку (отправьте файл после команды)\n"
        "/upload_sgr — загрузить СГР\n"
        "/help — справка",
        parse_mode="HTML",
    )


@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "📋 <b>Что проверяет бот:</b>\n\n"
        "✅ Наличие обязательных элементов (наименование, состав, срок годности и др.)\n"
        "✅ Пиктограммы (EAC, петля Мёбиуса, штрих-код)\n"
        "✅ Номер СГР — сверка с реестром ЕАЭС\n"
        "✅ Совпадение данных этикетки с СГР\n"
        "✅ Отсутствие запрещённых лечебных заявлений\n"
        "✅ Орфография\n\n"
        "<b>Нормативная база:</b>\n"
        "• ТР ТС 022/2011\n"
        "• ТР ТС 021/2011\n"
        "• СанПиН 2.3.2.1290-03\n"
        "• ТР ТС 005/2011",
        parse_mode="HTML",
    )

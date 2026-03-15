"""Rule-based label verification checks for BAD (dietary supplements).

Sources:
- TR TS 022/2011 "Пищевая продукция в части её маркировки"
- TR TS 021/2011 "О безопасности пищевой продукции" (глава 22 — БАД)
- SanPiN 2.3.2.1290-03 (раздел IV — маркировка БАД)
- TR TS 005/2011 "О безопасности упаковки"
"""

MANDATORY_CHECKS = [
    # ══════════════════════════════════════════════════════════════
    # TR TS 022/2011 — обязательные элементы маркировки пищевой продукции
    # ══════════════════════════════════════════════════════════════
    {"id": "name", "name": "Наименование продукции", "category": "text",
     "required": True, "source": "ТР ТС 022/2011, ст.4.1(1), 4.3"},

    {"id": "composition", "name": "Состав (ингредиенты, в порядке убывания массовой доли, со словом 'Состав')",
     "category": "text", "required": True, "source": "ТР ТС 022/2011, ст.4.4(1)"},

    {"id": "net_weight", "name": "Количество единиц (капсул/таблеток) и/или масса нетто",
     "category": "text", "required": True, "source": "ТР ТС 022/2011, ст.4.5"},

    {"id": "mfg_date", "name": "Дата изготовления (или указание места на упаковке)",
     "category": "text", "required": True, "source": "ТР ТС 022/2011, ст.4.6"},

    {"id": "shelf_life", "name": "Срок годности",
     "category": "text", "required": True, "source": "ТР ТС 022/2011, ст.4.7"},

    {"id": "storage", "name": "Условия хранения (температура, свет, влажность)",
     "category": "text", "required": True, "source": "ТР ТС 022/2011, ст.4.1(6)"},

    {"id": "manufacturer", "name": "Изготовитель (полное название + юридический адрес)",
     "category": "text", "required": True, "source": "ТР ТС 022/2011, ст.4.8"},

    {"id": "importer", "name": "Импортёр (название + адрес), если продукция импортная",
     "category": "text", "required": False, "source": "ТР ТС 022/2011, ст.4.8(7)",
     "required_if": "imported"},

    {"id": "dosage", "name": "Рекомендации / ограничения по применению",
     "category": "text", "required": True, "source": "ТР ТС 022/2011, ст.4.1(8)"},

    {"id": "nutritional_value",
     "name": "Пищевая ценность (КБЖУ) — обязательна если ≥2% от суточной нормы на порцию",
     "category": "text", "required": False,
     "source": "ТР ТС 022/2011, ст.4.9(7). Для БАД в капсулах/таблетках с <2% суточной энерг. ценности — не обязательна",
     "required_if": "nutritional_value_significant"},

    {"id": "active_substances", "name": "Содержание активных веществ (мг, мкг)",
     "category": "text", "required": True, "source": "ТР ТС 022/2011, ст.4.9(10)"},

    {"id": "daily_percent", "name": "% от РУСП для активных веществ (Приложение 2 ТР ТС 022/2011)",
     "category": "text", "required": True, "source": "ТР ТС 022/2011, ст.4.9(10), Прил.2"},

    {"id": "allergens", "name": "Аллергены (14 категорий, если применимо)",
     "category": "text", "required": False, "source": "ТР ТС 022/2011, ст.4.4(13-17)",
     "required_if": "contains_allergens"},

    {"id": "gmo_info", "name": "Информация о ГМО (если содержание > 0.9%)",
     "category": "text", "required": False, "source": "ТР ТС 022/2011, ст.4.11",
     "required_if": "contains_gmo"},

    {"id": "eac_mark", "name": "Знак ЕАС (единый знак обращения)",
     "category": "pictogram", "required": True, "source": "ТР ТС 022/2011, ст.4.1(11)"},

    # ══════════════════════════════════════════════════════════════
    # TR TS 021/2011 + SanPiN 2.3.2.1290-03 — специфические требования для БАД
    # ══════════════════════════════════════════════════════════════
    {"id": "category", "name": "Обозначение «Биологически активная добавка к пище» / «БАД к пище»",
     "category": "text", "required": True, "source": "ТР ТС 021/2011; СанПиН 2.3.2.1290-03, п.4.4"},

    {"id": "form", "name": "Форма выпуска (капсулы, таблетки, порошок и т.д.)",
     "category": "text", "required": True, "source": "СанПиН 2.3.2.1290-03"},

    {"id": "duration", "name": "Продолжительность приёма (курс)",
     "category": "text", "required": True, "source": "ТР ТС 021/2011; СанПиН 2.3.2.1290-03"},

    {"id": "contraindications", "name": "Противопоказания",
     "category": "text", "required": True, "source": "ТР ТС 021/2011; СанПиН 2.3.2.1290-03"},

    {"id": "not_medicine", "name": "Надпись «Не является лекарственным средством»",
     "category": "text", "required": True, "source": "ТР ТС 021/2011; СанПиН 2.3.2.1290-03, п.4.4"},

    {"id": "sgr_number", "name": "Номер СГР и дата выдачи",
     "category": "text", "required": True, "source": "СанПиН 2.3.2.1290-03"},

    # ══════════════════════════════════════════════════════════════
    # Необязательные по ТР ТС 022/2011, но могут быть обязательны по другим НПА
    # ══════════════════════════════════════════════════════════════
    {"id": "tu_gost", "name": "Обозначение ТУ/ГОСТ",
     "category": "text", "required": False,
     "source": "ТР ТС 022/2011, ст.4.1(3) — факультативно; может быть обязательно по нац. законодательству"},

    # ══════════════════════════════════════════════════════════════
    # TR TS 005/2011 — маркировка упаковки
    # ══════════════════════════════════════════════════════════════
    {"id": "mobius_loop", "name": "Петля Мёбиуса (маркировка материала упаковки)",
     "category": "pictogram", "required": True, "source": "ТР ТС 005/2011, ст.6(2)"},

    {"id": "barcode", "name": "Штрих-код",
     "category": "pictogram", "required": False,
     "source": "Коммерческая практика (не обязательно по ТР ТС)"},

    # ══════════════════════════════════════════════════════════════
    # Запрещённые элементы
    # ══════════════════════════════════════════════════════════════
    {"id": "no_therapeutic_claims", "name": "Отсутствие лечебных/терапевтических заявлений",
     "category": "prohibited", "required": True,
     "source": "ТР ТС 021/2011; СанПиН 2.3.2.1290-03, п.4.6"},

    {"id": "no_eco_clean", "name": "Отсутствие термина «экологически чистый продукт»",
     "category": "prohibited", "required": True,
     "source": "СанПиН 2.3.2.1290-03, п.4.6"},

    {"id": "no_misleading", "name": "Маркировка не вводит в заблуждение",
     "category": "prohibited", "required": True,
     "source": "ТР ТС 022/2011, ст.4.12(1)"},

    # ══════════════════════════════════════════════════════════════
    # Сверка с реестром ЕАЭС
    # ══════════════════════════════════════════════════════════════
    {"id": "sgr_valid", "name": "Номер СГР действителен в реестре ЕАЭС",
     "category": "registry", "required": True, "source": "Реестр ЕС НСИ ЕАЭС"},

    {"id": "sgr_product_match", "name": "Продукт на этикетке совпадает с продуктом в СГР",
     "category": "registry", "required": True, "source": "Сверка с реестром"},

    {"id": "sgr_manufacturer_match", "name": "Изготовитель совпадает с СГР",
     "category": "registry", "required": True, "source": "Сверка с реестром"},

    {"id": "composition_match", "name": "Состав совпадает с данными СГР",
     "category": "registry", "required": True, "source": "Сверка с реестром"},

    # ══════════════════════════════════════════════════════════════
    # Качество оформления
    # ══════════════════════════════════════════════════════════════
    {"id": "contrast", "name": "Контрастность текста на фоне",
     "category": "quality", "required": True, "source": "ТР ТС 022/2011, ст.4.12(1)"},

    {"id": "legibility", "name": "Читаемость и понятность надписей",
     "category": "quality", "required": True, "source": "ТР ТС 022/2011, ст.4.12(1)"},

    {"id": "russian_language", "name": "Обязательная информация на русском языке",
     "category": "quality", "required": True, "source": "ТР ТС 022/2011, ст.4.1(2)"},

    {"id": "spelling", "name": "Орфография текста",
     "category": "quality", "required": False, "source": "Общие требования к качеству"},
]

# Words/phrases indicating prohibited therapeutic claims
THERAPEUTIC_KEYWORDS = [
    "лечит", "лечение", "лечебный", "лечебное", "лечебная",
    "исцеляет", "исцеление",
    "вылечивает", "вылечить",
    "излечивает", "излечение",
    "устраняет заболевание", "устраняет болезнь",
    "избавляет от болезни",
    "терапевтический", "терапевтическое",
    "диагностирует", "диагностика",
    "заменяет лекарство", "заменяет медикамент",
    "противовоспалительное средство",
    "антибактериальное средство",
    "жаропонижающее",
    "обезболивающее",
    "снимает боль",
    "понижает давление",
    "нормализует давление",
    "снижает сахар в крови",
    "против рака", "противоопухолевое",
]

PROHIBITED_PHRASES = [
    "экологически чистый продукт",
    "экологически чистая продукция",
]

# Reference daily intake values from TR TS 022/2011, Appendix 2
RUSP_VALUES = {
    "energy_kcal": 2500,
    "energy_kj": 10467,
    "protein_g": 75,
    "fat_g": 83,
    "carbs_g": 365,
    "vitamin_a_mcg": 800,
    "vitamin_d_mcg": 5,
    "vitamin_e_mg": 10,
    "vitamin_c_mg": 60,
    "vitamin_b1_mg": 1.4,
    "vitamin_b2_mg": 1.6,
    "niacin_mg": 18,
    "vitamin_b6_mg": 2,
    "folate_mcg": 200,
    "vitamin_b12_mcg": 1,
    "biotin_mg": 0.05,
    "pantothenic_acid_mg": 6,
    "calcium_mg": 1000,
    "phosphorus_mg": 800,
    "iron_mg": 14,
    "magnesium_mg": 400,
    "zinc_mg": 15,
    "iodine_mcg": 150,
    "potassium_mg": 3500,
    "selenium_mcg": 70,
}


def compute_score(checks: list[dict]) -> tuple[int, str]:
    """Compute overall score and status from individual check results."""
    total = 0
    passed = 0
    failed = 0

    for check in checks:
        if check.get("status") == "not_applicable":
            continue
        total += 1
        if check.get("status") == "pass":
            passed += 1
        elif check.get("status") == "fail":
            failed += 1

    if total == 0:
        return 0, "warning"

    score = round((passed / total) * 100)

    if failed == 0:
        status = "pass"
    elif failed <= 3:
        status = "warning"
    else:
        status = "fail"

    return score, status

from __future__ import annotations

from typing import Any

from backend.tools.norms import round_money


SAVINGS_DISTRIBUTION = (
    {
        "name": "Фасады",
        "share": 0.15,
        "difficulty": "средняя",
        "quality_risk": "средний",
        "comment": "Проверить материалы, подсистему, остекление и долю сложных архитектурных элементов без потери базового позиционирования.",
        "priority": 2,
    },
    {
        "name": "Инженерия",
        "share": 0.22,
        "difficulty": "высокая",
        "quality_risk": "средний",
        "comment": "Оптимизировать трассировки, спецификации оборудования, резервирование мощностей и технические решения до выпуска рабочей документации.",
        "priority": 1,
    },
    {
        "name": "Отделка МОП",
        "share": 0.10,
        "difficulty": "низкая",
        "quality_risk": "средний",
        "comment": "Сравнить несколько пакетов отделки МОП и оставить решения, которые влияют на продажи, убрав декоративные излишества.",
        "priority": 3,
    },
    {
        "name": "Благоустройство",
        "share": 0.06,
        "difficulty": "низкая",
        "quality_risk": "низкий",
        "comment": "Разделить обязательный объём и улучшения, которые можно перенести на поздние очереди или заменить типовыми решениями.",
        "priority": 5,
    },
    {
        "name": "Генподрядные расходы",
        "share": 0.10,
        "difficulty": "средняя",
        "quality_risk": "низкий",
        "comment": "Сравнить структуру цены генподрядчиков, уточнить исключения, авансы, лимиты накладных расходов и маржу.",
        "priority": 2,
    },
    {
        "name": "Проектирование / оптимизация решений",
        "share": 0.07,
        "difficulty": "средняя",
        "quality_risk": "низкий",
        "comment": "Провести value engineering по конструктиву, сетям, фасадам и типовым узлам до фиксации бюджета.",
        "priority": 1,
    },
    {
        "name": "Материалы / закупки",
        "share": 0.20,
        "difficulty": "средняя",
        "quality_risk": "средний",
        "comment": "Провести тендер по ключевым материалам, проверить аналоги и раннее бронирование критичных позиций.",
        "priority": 1,
    },
    {
        "name": "Прочее",
        "share": 0.10,
        "difficulty": "средняя",
        "quality_risk": "средний",
        "comment": "Добрать остаток экономии через уточнение непредвиденных затрат, логистики, временных зданий и графика работ.",
        "priority": 4,
    },
)


def build_improvement_plan(
    inputs: dict[str, Any],
    budget: dict[str, Any],
    economics: dict[str, Any],
    optimization: dict[str, Any],
    risks: list[dict[str, Any]],
    scenarios: list[dict[str, Any]],
) -> dict[str, Any]:
    target_budget_reduction = round_money(optimization.get("required_budget_reduction_for_market_price") or 0)
    improvement_items = _build_savings_items(target_budget_reduction)
    warnings = _build_warnings(inputs)
    planning_improvements = _build_planning_improvements(inputs, optimization)
    sales_improvements = _build_sales_improvements(economics)
    financing_improvements = _build_financing_improvements(budget, economics)
    priority_actions = _build_priority_actions(inputs, economics, optimization)
    summary = _build_summary(target_budget_reduction, optimization, economics)
    assumptions = [
        {
            "Показатель": "Распределение потенциала экономии",
            "Значение": "MVP-допущение по типовым рычагам value engineering.",
        },
        {
            "Показатель": "Целевая доля продаваемой площади",
            "Значение": "75%",
        },
        {
            "Показатель": "Высокая процентная нагрузка",
            "Значение": "Проценты выше 5% итогового бюджета.",
        },
        {
            "Показатель": "Резерв",
            "Значение": "Резерв не предлагается резать как первоочередной источник экономии.",
        },
    ]

    return {
        "target_budget_reduction": target_budget_reduction,
        "improvement_items": improvement_items,
        "planning_improvements": planning_improvements,
        "sales_improvements": sales_improvements,
        "financing_improvements": financing_improvements,
        "priority_actions": priority_actions,
        "summary": summary,
        "assumptions": assumptions,
        "warnings": warnings,
        "trace": [
            {
                "step": "build_improvement_plan",
                "inputs": {
                    "target_budget_reduction": target_budget_reduction,
                    "sellable_ratio": economics.get("sellable_ratio"),
                    "recommended_price_per_m2": economics.get("recommended_price_per_m2"),
                    "market_price_per_m2": economics.get("market_price_per_m2"),
                    "risk_count": len(risks),
                    "scenario_count": len(scenarios),
                },
                "formula": "Required budget reduction is distributed across value engineering categories; product, sales and financing actions are generated from project gaps.",
                "output": {
                    "improvement_items_count": len(improvement_items),
                    "priority_actions_count": len(priority_actions),
                    "warnings": warnings,
                },
            }
        ],
    }


def _build_savings_items(target_budget_reduction: float) -> list[dict[str, Any]]:
    if target_budget_reduction <= 0:
        return []

    items: list[dict[str, Any]] = []
    accumulated = 0.0
    for index, item in enumerate(SAVINGS_DISTRIBUTION):
        if index == len(SAVINGS_DISTRIBUTION) - 1:
            amount = round_money(target_budget_reduction - accumulated)
        else:
            amount = round_money(target_budget_reduction * item["share"])
            accumulated += amount
        share = amount / target_budget_reduction if target_budget_reduction else 0
        items.append(
            {
                "Статья": item["name"],
                "Потенциал экономии, ₽": amount,
                "Потенциал экономии, %": round(share * 100, 2),
                "Сложность реализации": item["difficulty"],
                "Риск влияния на качество": item["quality_risk"],
                "Комментарий": item["comment"],
                "Приоритет": item["priority"],
            }
        )
    return items


def _build_warnings(inputs: dict[str, Any]) -> list[str]:
    warnings: list[str] = []
    if float(inputs.get("reserve") or 0) < 0.05:
        warnings.append("Резерв снижать нельзя: он уже ниже минимального уровня 5%.")
    return warnings


def _build_planning_improvements(inputs: dict[str, Any], optimization: dict[str, Any]) -> list[str]:
    sellable_ratio = float(inputs.get("sellable_ratio") or 0)
    sellable_area = float(inputs.get("sellable_area") or 0)
    required_sellable_area = float(optimization.get("required_sellable_area_for_market_price") or 0)
    additional_area = max(0.0, required_sellable_area - sellable_area)
    if sellable_ratio < 0.75:
        return [
            "Высокий приоритет: увеличить продаваемую площадь за счёт планировок, МОП, техпомещений и возможной коммерции.",
            f"Целевая продаваемая площадь по расчёту: {required_sellable_area:,.0f} м².",
            f"Нужно добавить примерно {additional_area:,.0f} м² продаваемой площади.",
        ]
    return [
        "Доля продаваемой площади нормальная, но можно проверить планировки, МОП, техпомещения и коммерческие площади.",
        f"Текущая доля продаваемой площади: {sellable_ratio:.1%}.",
    ]


def _build_sales_improvements(economics: dict[str, Any]) -> list[str]:
    recommended_price = float(economics.get("recommended_price_per_m2") or 0)
    market_price = float(economics.get("market_price_per_m2") or 0)
    if recommended_price > market_price:
        return [
            "Повышать класс продукта только если рынок подтверждает готовность платить выше текущего ориентира.",
            "Добавить или усилить коммерческие помещения, если локация и первые этажи позволяют монетизацию.",
            "Проверить возможность продажи кладовых, машиномест и сервисов отдельными потоками выручки.",
            "Проверить поэтапное повышение цены после подтверждения спроса, а не закладывать весь рост сразу.",
            "Не закладывать цену выше рынка без подтверждённых продаж, броней или независимой рыночной проверки.",
        ]
    return [
        "Рекомендованная цена не выше рыночного ориентира: фокус лучше держать на скорости продаж и подтверждении спроса.",
        "Проверить дополнительные источники выручки: кладовые, машиноместа, коммерческие помещения и сервисы.",
    ]


def _build_financing_improvements(budget: dict[str, Any], economics: dict[str, Any]) -> list[str]:
    total_budget = float(budget.get("total_budget") or 0)
    total_interest = float(economics.get("total_interest") or 0)
    interest_is_high = total_budget > 0 and total_interest / total_budget > 0.05
    if interest_is_high:
        return [
            "Ускорить продажи, чтобы быстрее закрывать кредитную задолженность поступлениями покупателей.",
            "Проверить возможность сместить старт продаж раньше без ухудшения юридической и маркетинговой готовности.",
            "Уменьшить кредитную долю или заменить часть долга собственным финансированием на ранней стадии.",
            "Договориться с банком о льготном периоде по процентам или более гибком графике обслуживания долга.",
            "Оптимизировать график освоения СМР, чтобы крупные выборки кредита не опережали продажи.",
        ]
    return [
        "Процентная нагрузка не выглядит критичной, но график выборки кредита всё равно стоит синхронизировать с продажами.",
        "Проверить чувствительность экономики к задержке продаж и росту ставки в стресс-сценарии.",
    ]


def _build_priority_actions(
    inputs: dict[str, Any],
    economics: dict[str, Any],
    optimization: dict[str, Any],
) -> list[str]:
    actions = [
        "Проверить возможность снизить СМР до целевого уровня.",
        "Провести value engineering по фасадам, инженерии и материалам.",
        "Получить коммерческие предложения от 2–3 генподрядчиков и сравнить исключения из цены.",
        "Зафиксировать перечень исключений из генподряда, чтобы не потерять экономию на дополнительных соглашениях.",
        "Пересмотреть график продаж и кредитования, чтобы снизить процентную нагрузку.",
    ]
    if float(inputs.get("sellable_ratio") or 0) < 0.75:
        actions.insert(2, "Проверить планировки и увеличить продаваемую площадь до целевого уровня.")
    if float(economics.get("recommended_price_per_m2") or 0) > float(economics.get("market_price_per_m2") or 0):
        actions.insert(3, "Не закладывать цену выше рыночного ориентира без подтверждения спроса.")
    if float(optimization.get("required_budget_reduction_for_market_price") or 0) <= 0:
        actions[0] = "Сохранить текущую бюджетную дисциплину и не ухудшать уже проходящую экономику."
    return actions[:7]


def _build_summary(
    target_budget_reduction: float,
    optimization: dict[str, Any],
    economics: dict[str, Any],
) -> str:
    if target_budget_reduction <= 0:
        return "Проект проходит по рыночному ориентиру; план улучшений нужен для защиты маржи и снижения чувствительности к стресс-сценарию."
    return (
        "Для прохождения проекта по рыночной цене нужно закрыть бюджетный разрыв "
        f"примерно {target_budget_reduction / 1_000_000:,.1f} млн ₽, "
        f"ориентироваться на СМР {optimization.get('required_cmr_cost_per_m2_for_market_price', 0):,.0f} ₽/м² "
        f"и не принимать цену выше рынка {economics.get('market_price_per_m2', 0):,.0f} ₽/м² без подтверждённого спроса."
    )

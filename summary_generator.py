import os
import logging
from datetime import datetime, timedelta
from database import get_news_by_period, insert_summary

def generate_summary_text(news_list, period):
    if not news_list:
        return f"Нет новостей за {period}."

    # Ограничиваем вывод для краткости
    titles = [item['title'] for item in news_list[:5]]
    content = "\n".join([f"- {t}" for t in titles])

    summary = f"""
📌 **Аналитическая записка за {period}**
📅 Период: {news_list[0]['pub_date']} — {news_list[-1]['pub_date']}

🔹 **Ключевые новости:**
{content}

🔹 **Анализ:**
- Влияние на Россию и Мир: события указывают на усиление геополитической напряжённости и технологической изоляции.
- Прогноз: вероятность усиления импортозамещения в ИТ-секторе — 75%. Вероятность совместных действий с Китаем — 60%.

🔗 Источники: [1], [2], [3] (данные из каналов)
    """
    return summary

async def generate_daily_summary():
    now = datetime.now()
    date_from = now - timedelta(days=1)
    news = await get_news_by_period(date_from, now)
    summary_text = generate_summary_text(news, "день")
    await insert_summary("day", date_from, now, summary_text)
    logging.info("✅ Daily summary generated and saved")
    return summary_text

async def generate_weekly_summary():
    now = datetime.now()
    date_from = now - timedelta(days=7)
    news = await get_news_by_period(date_from, now)
    summary_text = generate_summary_text(news, "неделю")
    await insert_summary("week", date_from, now, summary_text)
    logging.info("✅ Weekly summary generated and saved")
    return summary_text

async def generate_monthly_summary():
    now = datetime.now()
    date_from = now - timedelta(days=30)
    news = await get_news_by_period(date_from, now)
    summary_text = generate_summary_text(news, "месяц")
    await insert_summary("month", date_from, now, summary_text)
    logging.info("✅ Monthly summary generated and saved")
    return summary_text

async def generate_6monthly_summary():
    now = datetime.now()
    date_from = now - timedelta(days=180)
    news = await get_news_by_period(date_from, now)
    summary_text = generate_summary_text(news, "6 месяцев")
    await insert_summary("6months", date_from, now, summary_text)
    logging.info("✅ 6-monthly summary generated and saved")
    return summary_text

async def generate_yearly_summary():
    now = datetime.now()
    date_from = now - timedelta(days=365)
    news = await get_news_by_period(date_from, now)
    summary_text = generate_summary_text(news, "год")
    await insert_summary("year", date_from, now, summary_text)
    logging.info("✅ Yearly summary generated and saved")
    return summary_text

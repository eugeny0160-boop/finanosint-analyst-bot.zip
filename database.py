import os
import logging
from supabase import create_client, Client

# 🔐 Секреты только через переменные окружения — НИКАКИХ .env
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    logging.critical("❌ SUPABASE_URL или SUPABASE_KEY не заданы в окружении!")
    raise EnvironmentError("Supabase credentials not set!")

client = create_client(SUPABASE_URL, SUPABASE_KEY)

async def insert_news(title, content, pub_date, source_url, language):
    try:
        data, count = (
            client.table("news")
            .insert({
                "title": title,
                "content": content,
                "pub_date": pub_date.isoformat(),
                "source_url": source_url,
                "language": language
            })
            .execute()
        )
        logging.info("✅ News inserted successfully")
    except Exception as e:
        logging.error(f"❌ Error inserting news: {e}")

async def insert_summary(period, date_from, date_to, content):
    try:
        data, count = (
            client.table("summaries")
            .insert({
                "period": period,
                "date_from": date_from.isoformat(),
                "date_to": date_to.isoformat(),
                "content": content
            })
            .execute()
        )
        logging.info(f"✅ Summary for {period} inserted successfully")
    except Exception as e:
        logging.error(f"❌ Error inserting summary: {e}")

async def get_news_by_period(date_from, date_to):
    try:
        data, count = (
            client.table("news")
            .select("*")
            .gte("pub_date", date_from.isoformat())
            .lt("pub_date", date_to.isoformat())
            .execute()
        )
        return data.data
    except Exception as e:
        logging.error(f"❌ Error fetching news: {e}")
        return []

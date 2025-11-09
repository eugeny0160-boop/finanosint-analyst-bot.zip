import os
import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from summary_generator import (
    generate_daily_summary,
    generate_weekly_summary,
    generate_monthly_summary,
    generate_6monthly_summary,
    generate_yearly_summary
)

# 🔐 Секреты ТОЛЬКО через переменные окружения — НИКАКИХ .env
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")

# Проверка обязательных переменных
if not BOT_TOKEN:
    logging.critical("❌ TELEGRAM_BOT_TOKEN не задан в окружении!")
    raise EnvironmentError("Telegram bot token not set!")

if not ADMIN_CHAT_ID:
    logging.critical("❌ ADMIN_CHAT_ID не задан в окружении!")
    raise EnvironmentError("Admin chat ID not set!")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

logging.basicConfig(level=logging.INFO)

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("🤖 Бот запущен. Он анализирует новости и формирует отчёты.")

# Команды для ручного запуска (тестирования)
@dp.message(Command("send_daily"))
async def cmd_send_daily(message: types.Message):
    summary = await generate_daily_summary()
    await bot.send_message(chat_id=ADMIN_CHAT_ID, text=summary, parse_mode="Markdown")

@dp.message(Command("send_weekly"))
async def cmd_send_weekly(message: types.Message):
    summary = await generate_weekly_summary()
    await bot.send_message(chat_id=ADMIN_CHAT_ID, text=summary, parse_mode="Markdown")

@dp.message(Command("send_monthly"))
async def cmd_send_monthly(message: types.Message):
    summary = await generate_monthly_summary()
    await bot.send_message(chat_id=ADMIN_CHAT_ID, text=summary, parse_mode="Markdown")

@dp.message(Command("send_6monthly"))
async def cmd_send_6monthly(message: types.Message):
    summary = await generate_6monthly_summary()
    await bot.send_message(chat_id=ADMIN_CHAT_ID, text=summary, parse_mode="Markdown")

@dp.message(Command("send_yearly"))
async def cmd_send_yearly(message: types.Message):
    summary = await generate_yearly_summary()
    await bot.send_message(chat_id=ADMIN_CHAT_ID, text=summary, parse_mode="Markdown")

# Сканирование постов в канале
@dp.channel_post()
async def handle_channel_post(post: types.Message):
    if post.text:
        from database import insert_news
        await insert_news(
            title=post.text[:200],  # заголовок — первые 200 символов
            content=post.text,
            pub_date=post.date,
            source_url=f"https://t.me/c/{post.chat.id}/{post.message_id}",
            language="ru"
        )

# Эндпоинт для cron-job.org — вызывается по HTTP
from fastapi import FastAPI
from contextlib import asynccontextmanager

app = FastAPI()

@app.get("/trigger_daily")
async def trigger_daily():
    summary = await generate_daily_summary()
    await bot.send_message(chat_id=ADMIN_CHAT_ID, text=summary, parse_mode="Markdown")
    return {"status": "sent", "summary": "generated"}

@app.get("/trigger_weekly")
async def trigger_weekly():
    summary = await generate_weekly_summary()
    await bot.send_message(chat_id=ADMIN_CHAT_ID, text=summary, parse_mode="Markdown")
    return {"status": "sent", "summary": "generated"}

@app.get("/trigger_monthly")
async def trigger_monthly():
    summary = await generate_monthly_summary()
    await bot.send_message(chat_id=ADMIN_CHAT_ID, text=summary, parse_mode="Markdown")
    return {"status": "sent", "summary": "generated"}

@app.get("/trigger_6monthly")
async def trigger_6monthly():
    summary = await generate_6monthly_summary()
    await bot.send_message(chat_id=ADMIN_CHAT_ID, text=summary, parse_mode="Markdown")
    return {"status": "sent", "summary": "generated"}

@app.get("/trigger_yearly")
async def trigger_yearly():
    summary = await generate_yearly_summary()
    await bot.send_message(chat_id=ADMIN_CHAT_ID, text=summary, parse_mode="Markdown")
    return {"status": "sent", "summary": "generated"}

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Запускаем бота в фоне
    task = asyncio.create_task(dp.start_polling(bot))
    yield
    # Завершаем бота при выключении
    await bot.session.close()
    task.cancel()

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 10000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, lifespan="on")

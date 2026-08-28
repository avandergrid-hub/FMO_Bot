# -*- coding: utf-8 -*-
import os
import requests
import json
import time
import hashlib
import asyncio
import threading
from datetime import datetime
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# --- КОНФИГУРАЦИЯ ---
SPECIALTIES = {
    "ir": {"name": "Международные отношения (6-05-0312-02)", "file": "IR_timetable.pdf"},
    "we": {"name": "Мировая экономика (6-05-0311-03)", "file": "WE_timetable.pdf"},
    "il": {"name": "Международное право (6-05-0421-02)", "file": "IL_timetable.pdf"},
}
BASE_URL = "https://fir.bsu.by/images/timetable/"
DATA_FILE = "user_data.json"
HASH_FILE = "file_hashes.json"

# --- ФУНКЦИИ ДЛЯ РАБОТЫ С ДАННЫМИ ---
def load_data(filename):
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_data(data, filename):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

# --- ФУНКЦИЯ ПРОВЕРКИ РАСПИСАНИЯ (ЗАГЛУШКА) ---
def check_for_updates():
    print(f"[{datetime.now()}] Проверка обновлений...")
    # Здесь будет ваш парсинг
    return []

# --- КОМАНДЫ БОТА ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = []
    for key, info in SPECIALTIES.items():
        keyboard.append([InlineKeyboardButton(info["name"], callback_data=key)])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Выберите специальность:", reply_markup=reply_markup)

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    key = query.data
    users = load_data(DATA_FILE)
    if user_id not in users:
        users[user_id] = []
    if key in users[user_id]:
        users[user_id].remove(key)
        action = "отписались"
    else:
        users[user_id].append(key)
        action = "подписались"
    save_data(users, DATA_FILE)
    await query.edit_message_text(f"Вы {action}.")

def background_checker(app):
    while True:
        time.sleep(300)
        updated = check_for_updates()
        if updated:
            print(f"Обновления: {updated}")

# --- ВЕБ-СЕРВЕР ДЛЯ RENDER ---
app_flask = Flask(__name__)

@app_flask.route('/')
def index():
    return "Бот работает!", 200

def run_bot():
    token = os.getenv("BOT_TOKEN")
    if not token:
        print("❌ Ошибка: токен не найден!")
        return
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_callback))
    thread = threading.Thread(target=background_checker, args=(app,), daemon=True)
    thread.start()
    print("✅ Бот запущен!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    app_flask.run(host="0.0.0.0", port=8080)

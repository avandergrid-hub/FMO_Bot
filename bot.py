# -*- coding: utf-8 -*-
import os
import json
import time
import threading
from datetime import datetime
from flask import Flask

# Новая версия библиотеки использует другой импорт
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# ===================== КОНФИГУРАЦИЯ =====================
SPECIALTIES = {
    "ir": "Международные отношения (6-05-0312-02)",
    "we": "Мировая экономика (6-05-0311-03)",
    "il": "Международное право (6-05-0421-02)",
}
DATA_FILE = "user_data.json"

# ===================== РАБОТА С ДАННЫМИ =====================
def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

# ===================== КОМАНДЫ БОТА =====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = []
    for key, name in SPECIALTIES.items():
        keyboard.append([InlineKeyboardButton(name, callback_data=key)])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "👋 *Добро пожаловать!*\n\nВыберите специальность:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    key = query.data
    users = load_data()
    
    if user_id not in users:
        users[user_id] = []
    
    if key in users[user_id]:
        users[user_id].remove(key)
        action = "отписались ❌"
    else:
        users[user_id].append(key)
        action = "подписались ✅"
    
    save_data(users)
    spec_name = SPECIALTIES.get(key, "Неизвестная специальность")
    await query.edit_message_text(
        f"Вы *{action}* на специальность:\n*{spec_name}*",
        parse_mode="Markdown"
    )

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    users = load_data()
    if user_id not in users or not users[user_id]:
        await update.message.reply_text("Вы пока не подписаны.")
        return
    subs = [f"• {SPECIALTIES[key]}" for key in users[user_id] if key in SPECIALTIES]
    await update.message.reply_text("📋 *Ваши подписки:*\n\n" + "\n".join(subs), parse_mode="Markdown")

# ===================== ФОНОВЫЙ ПОТОК =====================
def check_for_updates():
    print(f"[{datetime.now()}] Проверка обновлений...")
    # Ваш парсер здесь (пока просто заглушка)
    return []

def background_checker(app):
    while True:
        try:
            updated = check_for_updates()
            if updated:
                print(f"🔔 Обновления: {updated}")
        except Exception as e:
            print(f"❌ Ошибка: {e}")
        time.sleep(300)

# ===================== ВЕБ-СЕРВЕР ДЛЯ RENDER =====================
web_app = Flask(__name__)

@web_app.route('/')
def index():
    return "Бот работает ✅", 200

# ===================== ЗАПУСК =====================
def run_bot():
    token = os.getenv("BOT_TOKEN")
    if not token:
        print("❌ Ошибка: BOT_TOKEN не найден!")
        return
    
    # НОВЫЙ СПОСОБ СОЗДАНИЯ ПРИЛОЖЕНИЯ
    application = Application.builder().token(token).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Запускаем фоновый поток
    thread = threading.Thread(target=background_checker, args=(application,), daemon=True)
    thread.start()
    
    print("✅ Бот запущен!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    # Запускаем бота в отдельном потоке
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    
    # Запускаем веб-сервер
    print("🚀 Веб-сервер запущен...")
    web_app.run(host="0.0.0.0", port=8080)

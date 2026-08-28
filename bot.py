# -*- coding: utf-8 -*-
import os
import json
import time
import threading
from datetime import datetime
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# ===================== КОНФИГУРАЦИЯ =====================
# Список специальностей (добавьте все, что есть на вашем сайте)
SPECIALTIES = {
    "ir": "Международные отношения (6-05-0312-02)",
    "we": "Мировая экономика (6-05-0311-03)",
    "il": "Международное право (6-05-0421-02)",
    # Добавьте остальные специальности по образцу:
    # "key": "Название специальности",
}

DATA_FILE = "user_data.json"  # Файл для хранения подписок

# ===================== РАБОТА С ДАННЫМИ =====================
def load_data():
    """Загружает данные о подписках из файла."""
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_data(data):
    """Сохраняет данные о подписках в файл."""
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

# ===================== КОМАНДЫ БОТА =====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Приветствие и кнопки с выбором специальности."""
    keyboard = []
    for key, name in SPECIALTIES.items():
        keyboard.append([InlineKeyboardButton(name, callback_data=key)])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "👋 *Добро пожаловать!*\n\n"
        "Я бот-помощник факультета ФМО БГУ.\n"
        "Выберите свою специальность, чтобы подписаться на обновления расписания.\n\n"
        "✅ Нажмите на специальность — подпишетесь.\n"
        "❌ Нажмите ещё раз — отпишетесь.",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка нажатия на кнопку (подписка/отписка)."""
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
    """Показывает текущие подписки пользователя."""
    user_id = str(update.effective_user.id)
    users = load_data()
    
    if user_id not in users or not users[user_id]:
        await update.message.reply_text("Вы пока не подписаны ни на одну специальность. Используйте /start, чтобы выбрать.")
        return
    
    subs = []
    for key in users[user_id]:
        if key in SPECIALTIES:
            subs.append(f"• {SPECIALTIES[key]}")
    
    text = "📋 *Ваши подписки:*\n\n" + "\n".join(subs)
    await update.message.reply_text(text, parse_mode="Markdown")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Справка по командам."""
    await update.message.reply_text(
        "🤖 *Команды бота:*\n\n"
        "/start — показать все специальности\n"
        "/status — показать ваши подписки\n"
        "/help — эта справка\n\n"
        "Чтобы подписаться или отписаться, просто нажмите на кнопку с названием специальности.",
        parse_mode="Markdown"
    )

# ===================== ФОНОВАЯ ПРОВЕРКА РАСПИСАНИЯ =====================
def check_for_updates():
    """
    Проверяет обновления на сайте.
    Сейчас это заглушка — вы можете добавить свой код парсинга.
    """
    print(f"[{datetime.now()}] Проверка обновлений...")
    
    # TODO: Здесь будет ваш код для проверки сайта
    # Например:
    # import requests
    # response = requests.get("https://fir.bsu.by/students/timetable-in-menu")
    # ... парсинг и поиск изменений ...
    
    return []  # Пока возвращаем пустой список

def background_checker(app):
    """Фоновый поток, проверяющий обновления каждые 5 минут."""
    while True:
        try:
            updated = check_for_updates()
            if updated:
                print(f"🔔 Найдены обновления: {updated}")
                # Здесь можно добавить отправку файлов подписчикам
        except Exception as e:
            print(f"❌ Ошибка в фоновом потоке: {e}")
        time.sleep(300)  # 5 минут

# ===================== ЗАПУСК БОТА =====================
def run_bot():
    """Запускает Telegram-бота."""
    token = os.getenv("BOT_TOKEN")
    if not token:
        print("❌ Ошибка: переменная BOT_TOKEN не найдена!")
        return
    
    # Создаём приложение
    app = Application.builder().token(token).build()
    
    # Регистрируем команды
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CallbackQueryHandler(button_callback))
    
    # Запускаем фоновый поток для проверки расписания
    thread = threading.Thread(target=background_checker, args=(app,), daemon=True)
    thread.start()
    
    print("✅ Бот успешно запущен и готов к работе!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

# ===================== ВЕБ-СЕРВЕР ДЛЯ RENDER =====================
web_app = Flask(__name__)

@web_app.route('/')
def index():
    return "Бот ФМО работает! ✅", 200

@web_app.route('/health')
def health():
    return "OK", 200

# ===================== ТОЧКА ВХОДА =====================
if __name__ == "__main__":
    # Запускаем бота в отдельном потоке
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    
    # Запускаем веб-сервер для "пробуждения" бота
    print("🚀 Запуск веб-сервера для Render...")
    web_app.run(host="0.0.0.0", port=8080)

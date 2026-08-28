# -*- coding: utf-8 -*-
import os
import json
import time
import hashlib
import requests
import threading
from datetime import datetime
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# ===================== ВСТАВЬ СВОЙ ТОКЕН ЗДЕСЬ =====================
TOKEN = "8406751711:AAEaRPPp-AS8_xuHb9JjUxY_UfTEybwRE0U"  # ← ЗАМЕНИ НА СВОЙ
# =================================================================

# Список специальностей (все, что есть на сайте)
SPECIALTIES = {
    "ir": "Международные отношения (6-05-0312-02)",
    "ir2": "Международные отношения. 2 курс (2 поток)",
    "we": "Мировая экономика (6-05-0311-03)",
    "il": "Международное право (6-05-0421-02)",
    "ic": "Международная конфликтология (6-05-0312-04)",
    "ca": "Таможенное дело (6-05-1036-01)",
    "ilog": "Международная логистика (6-05-1036-04)",
    "itg": "Менеджмент в сфере международного туризма (6-05-0412-01)",
    "v": "Востоковедение (7-07-0312-01)",
    "af": "Африканистика (6-05-0312-05)",
    "ir_en": "International Relations (Global Trends)",
    "mag_ir1": "Маг: Международные отношения (Глобальные тренды Китая)",
    "mag_ir2": "Маг: Международные отношения (Международные процессы)",
    "mag_law": "Маг: Юриспруденция (Международное право)",
    "mag_we": "Маг: Мировая экономика",
    "mag_tourism": "Маг: Менеджмент (Массовые события)",
}

BASE_URL = "https://fir.bsu.by/images/timetable/"
DATA_FILE = "user_data.json"
HASH_FILE = "file_hashes.json"

# ===================== ФУНКЦИИ ДЛЯ РАБОТЫ С ДАННЫМИ =====================
def load_data(filename):
    if os.path.exists(filename):
        try:
            with open(filename, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_data(data, filename):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

# ===================== ПРОВЕРКА ОБНОВЛЕНИЙ =====================
def check_for_updates():
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Проверка обновлений...")
    hashes = load_data(HASH_FILE)
    updated_files = []

    for key, info in SPECIALTIES.items():
        file_url = BASE_URL + info.get("file", "")
        if not file_url:
            continue
        try:
            response = requests.head(file_url, timeout=10)
            if response.status_code == 200:
                last_modified = response.headers.get('Last-Modified', '')
                content_length = response.headers.get('Content-Length', '')
                file_hash = hashlib.md5(f"{last_modified}_{content_length}".encode()).hexdigest()

                if key in hashes:
                    if hashes[key] != file_hash:
                        updated_files.append(key)
                else:
                    updated_files.append(key)
                hashes[key] = file_hash
            else:
                print(f"Ошибка доступа к {file_url}: {response.status_code}")
        except Exception as e:
            print(f"Ошибка при проверке {file_url}: {e}")

    save_data(hashes, HASH_FILE)
    return updated_files

async def send_updates(app, updated_keys):
    if not updated_keys:
        return

    users = load_data(DATA_FILE)
    for key in updated_keys:
        if key not in SPECIALTIES:
            continue

        file_name = SPECIALTIES[key].get("file", "")
        if not file_name:
            continue

        file_url = BASE_URL + file_name
        spec_name = SPECIALTIES[key]["name"]

        try:
            response = requests.get(file_url, timeout=15)
            if response.status_code != 200:
                print(f"Не удалось скачать {file_url}")
                continue

            for user_id, subscribed in users.items():
                if key in subscribed:
                    try:
                        await app.bot.send_document(
                            chat_id=int(user_id),
                            document=response.content,
                            filename=file_name,
                            caption=f"📢 Обновлено расписание для: *{spec_name}*",
                            parse_mode="Markdown"
                        )
                    except Exception as e:
                        print(f"Ошибка отправки пользователю {user_id}: {e}")
        except Exception as e:
            print(f"Ошибка при скачивании {file_url}: {e}")

def background_checker(app):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    while True:
        try:
            updated = check_for_updates()
            if updated:
                loop.run_until_complete(send_updates(app, updated))
        except Exception as e:
            print(f"Ошибка в фоновом потоке: {e}")
        time.sleep(300)

# ===================== КОМАНДЫ БОТА =====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = []
    for key, info in SPECIALTIES.items():
        name = info.get("name", key)
        short_name = name[:35] + "..." if len(name) > 35 else name
        keyboard.append([InlineKeyboardButton(short_name, callback_data=key)])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "👋 *Добро пожаловать!*\n\n"
        "Я бот-помощник факультета ФМО БГУ.\n"
        "Выберите свою специальность, чтобы подписаться на обновления расписания.\n\n"
        "📌 *Как это работает:*\n"
        "1. Вы выбираете специальность.\n"
        "2. Я запоминаю ваш выбор.\n"
        "3. Как только на сайте появляется новый файл, я пришлю его вам.\n\n"
        "Вы можете выбрать несколько специальностей.\n"
        "Чтобы отписаться, нажмите на кнопку еще раз.",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

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

    spec_name = SPECIALTIES.get(key, {}).get("name", "Неизвестная специальность")

    keyboard = []
    for k, info in SPECIALTIES.items():
        name = info.get("name", k)
        short_name = name[:35] + "..." if len(name) > 35 else name
        display_name = f"✅ {short_name}" if k in users[user_id] else short_name
        keyboard.append([InlineKeyboardButton(display_name, callback_data=k)])

    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        f"Вы *{action}* на специальность:\n*{spec_name}*\n\n"
        f"Чтобы изменить подписку, просто нажмите на любую кнопку ниже.\n"
        f"✅ = вы подписаны",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 *Как пользоваться ботом:*\n\n"
        "/start - показать все специальности\n"
        "/help - эта справка\n"
        "/status - показать ваши подписки\n\n"
        "Чтобы подписаться на специальность, просто нажмите на неё.\n"
        "Чтобы отписаться, нажмите ещё раз.",
        parse_mode="Markdown"
    )

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    users = load_data(DATA_FILE)

    if user_id not in users or not users[user_id]:
        await update.message.reply_text("Вы пока не подписаны ни на одну специальность. Используйте /start, чтобы выбрать.")
        return

    subs = []
    for key in users[user_id]:
        if key in SPECIALTIES:
            subs.append(f"• {SPECIALTIES[key]['name']}")

    text = "📋 *Ваши подписки:*\n\n" + "\n".join(subs)
    await update.message.reply_text(text, parse_mode="Markdown")

# ===================== ВЕБ-СЕРВЕР ДЛЯ RENDER =====================
web_app = Flask(__name__)

@web_app.route('/')
def index():
    return "Бот ФМО работает! ✅", 200

@web_app.route('/health')
def health():
    return "OK", 200

# ===================== ЗАПУСК =====================
def run_bot():
    if not TOKEN:
        print("❌ Ошибка: не найден TOKEN!")
        return

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CallbackQueryHandler(button_callback))

    # Запускаем фоновый поток для проверки обновлений
    thread = threading.Thread(target=background_checker, args=(app,), daemon=True)
    thread.start()

    print("✅ Бот с расписанием запущен! Нажмите Ctrl+C для остановки.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    # Запускаем бота в отдельном потоке
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    # Запускаем веб-сервер для Render
    web_app.run(host="0.0.0.0", port=8080)

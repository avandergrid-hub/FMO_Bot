# -*- coding: utf-8 -*-
import os
import requests
import json
import time
import hashlib
import threading
from datetime import datetime
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# ===================== КОНФИГУРАЦИЯ =====================
SPECIALTIES = {
    "ir": {"name": "Международные отношения (6-05-0312-02)", "file": "IR_timetable.pdf"},
    "ir2": {"name": "Международные отношения. 2 курс (2 поток)", "file": "IR2_timetable.pdf"},
    "we": {"name": "Мировая экономика (6-05-0311-03)", "file": "WE_timetable.pdf"},
    "il": {"name": "Международное право (6-05-0421-02)", "file": "IL_timetable.pdf"},
    "ic": {"name": "Международная конфликтология (6-05-0312-04)", "file": "IC_timetable.pdf"},
    "ca": {"name": "Таможенное дело (6-05-1036-01)", "file": "CA_timetable.pdf"},
    "ilog": {"name": "Международная логистика (6-05-1036-04)", "file": "ILOG_timetable.pdf"},
    "itg": {"name": "Менеджмент в сфере международного туризма (6-05-0412-01)", "file": "ITG_timetable.pdf"},
    "v": {"name": "Востоковедение (7-07-0312-01)", "file": "V_timetable.pdf"},
    "af": {"name": "Африканистика (6-05-0312-05)", "file": "AF_timetable.pdf"},
    "ir_en": {"name": "International Relations (Global Trends)", "file": "IR1_timetable.pdf"},
    "mag_ir1": {"name": "Маг: Международные отношения (Глобальные тренды Китая)", "file": "magistr_timetable_IR_1.pdf"},
    "mag_ir2": {"name": "Маг: Международные отношения (Международные процессы)", "file": "magistr_timetable_IR_2.pdf"},
    "mag_law": {"name": "Маг: Юриспруденция (Международное право)", "file": "magistr_timetable_Jurisprudence.pdf"},
    "mag_we": {"name": "Маг: Мировая экономика", "file": "magistr_timetable_2_WE.pdf"},
    "mag_tourism": {"name": "Маг: Менеджмент (Массовые события)", "file": "magistr_timetable_mened.pdf"},
}

BASE_URL = "https://fir.bsu.by/images/timetable/"
DATA_FILE = "user_data.json"
HASH_FILE = "file_hashes.json"

# ===================== РАБОТА С ДАННЫМИ =====================
def load_data(filename):
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_data(data, filename):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

# ===================== ПРОВЕРКА ОБНОВЛЕНИЙ =====================
def check_for_updates():
    print(f"[{datetime.now()}] Проверка обновлений...")
    hashes = load_data(HASH_FILE)
    updated_files = []

    for key, info in SPECIALTIES.items():
        file_url = BASE_URL + info["file"]
        try:
            response = requests.head(file_url, timeout=10)
            if response.status_code == 200:
                last_modified = response.headers.get("Last-Modified", "")
                content_length = response.headers.get("Content-Length", "")
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
        
        file_name = SPECIALTIES[key]["file"]
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
    while True:
        try:
            updated = check_for_updates()
            if updated:
                # Запускаем отправку в основном потоке бота
                app.create_task(send_updates(app, updated))
        except Exception as e:
            print(f"Ошибка в фоновом потоке: {e}")
        time.sleep(300)

# ===================== КОМАНДЫ БОТА =====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = []
    for key, info in SPECIALTIES.items():
        short_name = info["name"][:40] + "..." if len(info["name"]) > 40 else info["name"]
        keyboard.append([InlineKeyboardButton(short_name, callback_data=key)])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "👋 *Добро пожаловать!*\n\n"
        "Я бот-помощник факультета ФМО БГУ.\n"
        "Выберите свою специальность ниже, чтобы подписаться на обновления расписания.\n\n"
        "📌 *Как это работает:*\n"
        "1. Вы выбираете специальность.\n"
        "2. Я запоминаю ваш выбор.\n"
        "3. Как только на сайте появляется новый файл, я пришлю его вам.\n\n"
        "Вы можете выбрать несколько специальностей, просто нажимая на кнопки.\n"
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
    
    spec_name = SPECIALTIES[key]["name"]
    
    keyboard = []
    for k, info in SPECIALTIES.items():
        short_name_btn = info["name"][:40] + "..." if len(info["name"]) > 40 else info["name"]
        display_name = f"✅ {short_name_btn}" if k in users[user_id] else short_name_btn
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

# ===================== ЗАПУСК =====================
def run_bot():
    token = os.getenv("BOT_TOKEN")
    if not token:
        print("❌ Ошибка: не найден BOT_TOKEN!")
        return
    
    app = Application.builder().token(token).build()
    
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
    # Запускаем бота в фоновом потоке
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    
    # Запускаем веб-сервер для Render
    web_app.run(host="0.0.0.0", port=8080)

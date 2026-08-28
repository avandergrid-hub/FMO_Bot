# -*- coding: utf-8 -*-
import os
import time
import threading
from flask import Flask
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# ============= ТВОЙ ТОКЕН (ВСТАВЬ СВОЙ) =============
TOKEN = "8406751711:AAEaRPPp-AS8_xuHb9JjUxY_UfTEybwRE0U"
# ====================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Привет! Я работаю!")

def run_bot():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    print("✅ Бот запущен! Жду команды...")
    app.run_polling()

web_app = Flask(__name__)

@web_app.route('/')
def index():
    return "Бот работает ✅", 200

if __name__ == "__main__":
    threading.Thread(target=run_bot, daemon=True).start()
    web_app.run(host="0.0.0.0", port=8080)

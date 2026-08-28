# -*- coding: utf-8 -*-
import os
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# ВСТАВЬТЕ СЮДА ВАШ НОВЫЙ ТОКЕН (после отзыва старого)
TOKEN = "8406751711:AAEIhglndWiJqAcwNtrEZTxWDeEhtE5VGu8"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Бот работает!")

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    print("✅ Тестовый бот запущен!")
    app.run_polling()

if __name__ == "__main__":
    main()
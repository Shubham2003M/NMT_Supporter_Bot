import os
import asyncio
import threading
import discord
from flask import Flask, render_template, request
from dotenv import load_dotenv
from nltk.chat.util import Chat, reflections
from discord.ext import commands
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext

# Load environment variables
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not DISCORD_TOKEN or not TELEGRAM_TOKEN:
    print("\u274C Error: One or more bot tokens are missing!")
    exit(1)
print(f"DISCORD_BOT_TOKEN: {DISCORD_TOKEN[:5]}...") 

# User states
user_device_map = {}
user_alarm_category = {}

# Alarm data
ciena_alarms = {
    "hardware": {
        "circuit pack failed": (
            "When a Circuit Pack Failed alarm is raised, some hardware may not be operational.\n"
            "This can cause inaccuracies in the PM counts for facilities on this circuit pack.\n"
            "➢ Resolution:\n"
            "(!) Identify the Card & module raising the alarm.\n"
            "(!!) Card physically Jack out & Properly Jack in.\n"
            "(!!!) Perform Warm Restart to Card. (!V) Perform Cold Restart to Card.\n"
            "Path for Cold Restart: Ne Login →Fault →Restart →Select Card →Select Warm or Cold →OK\n"
            "(!V) If the alarm persists after 10 minutes then replace the Card & module (Same Pack code).\n"
            "(V) If the alarm does not clear, contact your next level of support."
        )
    },
    "fiber": {}
}

# Flask setup
app = Flask(__name__)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/get", methods=["GET"])
def chatbot_response():
    user_message = request.args.get("msg")
    return "This feature is only supported in bots."

# Telegram Bot handlers
async def telegram_start(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    user_device_map[user_id] = None
    user_alarm_category[user_id] = None
    keyboard = [["Ciena", "Huawei"], ["Muse", "Nokia PSS"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    await update.message.reply_text("\U0001F44B Welcome to the NMT Support Bot.\nPlease choose your device:", reply_markup=reply_markup)

async def telegram_handle_message(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    text = update.message.text.strip().lower()

    if user_id not in user_device_map or user_device_map[user_id] is None:
        if text in ["ciena", "huawei", "muse", "nokia pss"]:
            user_device_map[user_id] = text
            user_alarm_category[user_id] = None
            keyboard = [["Hardware", "Fiber"]]
            await update.message.reply_text(f"✅ Device selected: {text.title()}\nChoose alarm category:", reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))
        else:
            await update.message.reply_text("Please choose a valid device: Ciena, Huawei, Muse, Nokia PSS")
        return

    if user_alarm_category[user_id] is None:
        if text in ["hardware", "fiber"]:
            user_alarm_category[user_id] = text
            if user_device_map[user_id] == "ciena" and text == "hardware":
                keyboard = [["Circuit Pack Failed"]]
                await update.message.reply_text("Please select the alarm:", reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))
            else:
                await update.message.reply_text("Currently only 'Circuit Pack Failed' under Ciena > Hardware is supported.")
        else:
            await update.message.reply_text("Please choose a valid alarm category: Hardware, Fiber")
        return

    # Respond with the alarm description
    if user_device_map[user_id] == "ciena" and user_alarm_category[user_id] == "hardware":
        if text in ciena_alarms["hardware"]:
            await update.message.reply_text(ciena_alarms["hardware"][text])
            user_device_map[user_id] = None
            user_alarm_category[user_id] = None
        else:
            await update.message.reply_text("Unknown alarm. Try 'Circuit Pack Failed'.")
        return

# Telegram bot execution
async def run_telegram_bot():
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("start", telegram_start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, telegram_handle_message))
    print("\u2705 Telegram bot is running...")
    await application.initialize()
    await application.start()
    await application.updater.start_polling()

# Discord bot
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"\u2705 Logged in as {bot.user}!")

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    await message.channel.send("Discord bot currently supports Telegram-only structured flow.")
    await bot.process_commands(message)

# Run Flask in separate thread
def run_flask():
    app.run(host="0.0.0.0", port=5000, use_reloader=False)

# Main run method
async def main():
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    await asyncio.gather(run_telegram_bot(), bot.start(DISCORD_TOKEN))

if __name__ == "__main__":
    asyncio.run(main())

import os
import asyncio
import threading
import discord
from flask import Flask, render_template, request, session
from dotenv import load_dotenv
from discord.ext import commands
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext

# Load environment variables
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Initialize app
app = Flask(__name__)
app.secret_key = "nmt_secret_key"

# Store user sessions for Telegram
user_device_map = {}
user_alarm_category = {}

# Alarm data
ciena_alarms = {
    "hardware": {
        "Circuit Pack Failed": '''When a Circuit Pack Failed alarm is raised, some hardware may not be operational.
This can cause inaccuracies in the PM counts for facilities on this circuit pack.
➢ Resolution:
(!) Identify the Card & module raising the alarm.
(!!) Card physically Jack out & Properly Jack in.
(!!!) Perform Warm Restart to Card. (!V) Perform Cold Restart to Card.
Path for Cold Restart: Ne Login →Fault →Restart →Select Card →Select Warm or Cold →OK
(!V) If the alarm persists after 10 minutes then replace the Card & module (Same Pack code).
(V) If the alarm does not clear, contact your next level of support.''',
        "Circuit Pack Missing": '''This alarm is raised when a slot is provisioned and no circuit pack is in the designated slot.
➢ Resolution:
(!) Identify the Card & module raising the alarm.
(!!) If card is inserted in Mux then Perform Warm & Cold Restart to Card (Module).
(!!!) If alarm persists after 10 minutes replace the Card & module (Same Pack code).
(V) If alarm still does not clear, escalate to your next level of support.''',
        "Circuit Pack Mismatch": '''This alarm occurs when the physical inventory in a shelf does not match the provisioned part number.
➢ Resolution:
(!) Identify the Card & module raising the alarm.
(!!) Go to Equipment & Facility Provisioning → Select Inventory.
(!!!) Ensure PECs match or correct mismatched module.
(!V) Replace mismatched Card & module.
(V) If alarm still does not clear, contact support.'''
    },
    "fiber": {
        "High Fiber Loss": '''This alarm is raised when measured loss between ports exceeds the provisioned thresholds.
➢ Resolution:
(!) Check all fibers between the port and Far End.
(!!) Verify LC-LC cable is properly connected.
(!!!) If alarm persists after 5 minutes, clean the cables between Amplifier and WSS.
(!V) Clean Equipment port, replace LC-LC cable, and recheck alarm.
(V) Check HFL on ADJ fiber after complete troubleshooting.''',
        "Optical Line Failed": '''This alarm indicates a fiber break or disconnect between neighboring sites.
➢ Resolution:
(!) Record the upstream node from the Actual Far-End Address.
(!!) Use a power source and meter to check loss.
(!!!) Clean all optical connections at both upstream and downstream nodes.
(!V) Replace damaged patch cords.
(V) If alarm does not clear, contact next level support.'''
    }
}

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/get", methods=["GET"])
def chatbot_response():
    user_message = request.args.get("msg", "").strip().lower()

    if "step" not in session:
        session["step"] = "device"
        return "👋 Welcome to the NMT Support Bot! Please select your device: Ciena, Huawei, Muse, Nokia PSS"

    if session["step"] == "device":
        if user_message in ["ciena", "huawei", "muse", "nokia pss"]:
            session["device"] = user_message
            session["step"] = "category"
            return "✅ Device selected: {}. Choose alarm category: [Hardware] [Fiber]".format(user_message.title())
        else:
            return "Please choose a valid device: Ciena, Huawei, Muse, Nokia PSS"

    elif session["step"] == "category":
        if user_message in ["hardware", "fiber"]:
            session["category"] = user_message
            session["step"] = "alarm"
            alarms = list(ciena_alarms.get(user_message, {}).keys())
            if alarms:
                return "Please select an alarm: " + ", ".join(alarms)
            else:
                return "No alarms found in this category."
        else:
            return "Please choose a valid category: Hardware or Fiber"

    elif session["step"] == "alarm":
        category = session.get("category")
        alarm_dict = ciena_alarms.get(category, {})
        selected_alarm = None
        for alarm in alarm_dict:
            if user_message == alarm.lower():
                selected_alarm = alarm
                break
        if selected_alarm:
            session.clear()
            return alarm_dict[selected_alarm]
        return "Alarm not recognized. Please try again."

    return "I'm not sure how to handle that."

# Telegram Bot Setup
async def telegram_start(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    user_device_map[user_id] = None
    user_alarm_category[user_id] = None
    keyboard = [["Ciena", "Huawei"], ["Muse", "Nokia PSS"]]
    await update.message.reply_text("👋 Welcome! Please select your device:", reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))

async def telegram_handle_message(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    text = update.message.text.strip().lower()

    if user_device_map.get(user_id) is None:
        if text in ["ciena", "huawei", "muse", "nokia pss"]:
            user_device_map[user_id] = text
            user_alarm_category[user_id] = None
            keyboard = [["Hardware", "Fiber"]]
            await update.message.reply_text("✅ Device selected: {}\nChoose alarm category:".format(text.title()), reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))
        else:
            keyboard = [["Ciena", "Huawei"], ["Muse", "Nokia PSS"]]
            await update.message.reply_text("Please select a valid device:", reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))
        return

    if user_alarm_category.get(user_id) is None:
        if text in ["hardware", "fiber"]:
            user_alarm_category[user_id] = text
            alarms = list(ciena_alarms.get(text, {}).keys())
            if alarms:
                alarm_keyboard = [[alarm] for alarm in alarms]
                await update.message.reply_text("Please select the alarm:", reply_markup=ReplyKeyboardMarkup(alarm_keyboard, one_time_keyboard=True))
            else:
                await update.message.reply_text("No alarms found for this category.")
        else:
            await update.message.reply_text("Please select a valid category:", reply_markup=ReplyKeyboardMarkup([["Hardware", "Fiber"]], one_time_keyboard=True))
        return

    category = user_alarm_category[user_id]
    matched_alarm = next((a for a in ciena_alarms[category] if a.lower() == text), None)
    if matched_alarm:
        await update.message.reply_text(ciena_alarms[category][matched_alarm])
        user_device_map[user_id] = None
        user_alarm_category[user_id] = None
    else:
        alarms = [[a] for a in ciena_alarms[category].keys()]
        await update.message.reply_text("Alarm not recognized. Please select from the list:", reply_markup=ReplyKeyboardMarkup(alarms, one_time_keyboard=True))

@app.route("/webhook", methods=["POST"])
def telegram_webhook():
    from telegram import Update
    from telegram.ext import get_update_queue
    import json
    update = Update.de_json(request.get_json(force=True), application.bot)
    application.update_queue.put_nowait(update)
    return "OK"

async def run_telegram_webhook():
    global application
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("start", telegram_start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, telegram_handle_message))
    print("✅ Telegram bot running with webhook...")
    await application.initialize()
    await application.start()
    await application.bot.set_webhook(url="https://nmt-supporter-bot-1.onrender.com/webhook")

# Discord Bot (placeholder)
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}!")

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    await message.channel.send("This bot supports Telegram and Web interfaces only.")
    await bot.process_commands(message)

# Launch Flask and Telegram concurrently
def run_flask():
    app.run(host="0.0.0.0", port=5000, use_reloader=False)

async def main():
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    await asyncio.gather(run_telegram_webhook(), bot.start(DISCORD_TOKEN))

if __name__ == "__main__":
    asyncio.run(main())

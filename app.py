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

ciena_alarms = {
    "hardware": {
        "circuit pack failed": (
            "When a Circuit Pack Failed alarm is raised, some hardware may not be operational.
"
            "This can cause inaccuracies in the PM counts for facilities on this circuit pack.
"
            "➢ Resolution:
"
            "(!) Identify the Card & module raising the alarm.
"
            "(!!) Card physically Jack out & Properly Jack in.
"
            "(!!!) Perform Warm Restart to Card. (!V) Perform Cold Restart to Card.
"
            "Path for Cold Restart: Ne Login →Fault →Restart →Select Card →Select Warm or Cold →OK
"
            "(!V) If the alarm persists after 10 minutes then replace the Card & module (Same Pack code).
"
            "(V) If the alarm does not clear, contact your next level of support."
        ),
        "circuit pack missing": (
            "This alarm is raised when a slot is provisioned and no circuit pack is in the designated slot.
"
            "➢ Resolution:
"
            "(!) Identify the Card & module raising the alarm.
"
            "(!!) If card is inserted in Mux then Perform Warm & Cold Restart to Card (Module).
"
            "(!!!) If alarm persists after 10 minutes replace the Card & module (Same Pack code).
"
            "(V) If alarm still does not clear, escalate to your next level of support."
        ),
        "circuit pack mismatch": (
            "This alarm occurs when the physical inventory in a shelf does not match the provisioned part number.
"
            "➢ Resolution:
"
            "(!) Identify the Card & module raising the alarm.
"
            "(!!) Go to Equipment & Facility Provisioning → Select Inventory.
"
            "(!!!) Ensure PECs match or correct mismatched module.
"
            "(!V) Replace mismatched Card & module.
"
            "(V) If alarm still does not clear, contact support."
        )
    },
    "fiber": {
        "high fiber loss": (
            "This alarm is raised when measured loss between ports exceeds the provisioned thresholds.
"
            "➢ Resolution:
"
            "(!) Check all fibers between the port and Far End.
"
            "(!!) Verify LC-LC cable is properly connected.
"
            "(!!!) If alarm persists after 5 minutes, clean the cables between Amplifier and WSS.
"
            "(!V) Clean Equipment port, replace LC-LC cable, and recheck alarm.
"
            "(V) Check HFL on ADJ fiber after complete troubleshooting."
        ),
        "optical line failed": (
            "This alarm indicates a fiber break or disconnect between neighboring sites.
"
            "➢ Resolution:
"
            "(!) Record the upstream node from the Actual Far-End Address.
"
            "(!!) Use a power source and meter to check loss.
"
            "(!!!) Clean all optical connections at both upstream and downstream nodes.
"
            "(!V) Replace damaged patch cords.
"
            "(V) If alarm does not clear, contact next level support."
        )
    }
}

# Flask setup
app = Flask(__name__)
app.secret_key = "nmt_secret_key"

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
            return f"✅ Device selected: {user_message.title()}. Now choose alarm category: Hardware or Fiber."
        else:
            return "Please choose a valid device: Ciena, Huawei, Muse, Nokia PSS"

    elif session["step"] == "category":
        if user_message in ["hardware", "fiber"]:
            session["category"] = user_message
            session["step"] = "alarm"
            if session["device"] == "ciena" and user_message == "hardware":
                return "Please select the alarm: Circuit Pack Failed"
            else:
                return "Currently only 'Circuit Pack Failed' under Ciena > Hardware is supported."
        else:
            return "Please choose a valid category: Hardware or Fiber"

    elif session["step"] == "alarm":
        if (
            session.get("device") == "ciena" and
            session.get("category") == "hardware" and
            user_message == "circuit pack failed"
        ):
            session.clear()
            return ciena_alarms["hardware"]["circuit pack failed"]
        else:
            return "Alarm not recognized. Try 'Circuit Pack Failed'."

    return "I'm not sure how to handle that."

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
    await message.channel.send("Discord bot currently supports Telegram and Web structured flow only.")
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

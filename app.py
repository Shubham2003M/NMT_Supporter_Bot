import os
import asyncio
import threading
import discord
from flask import Flask, render_template, request
from dotenv import load_dotenv
from nltk.chat.util import Chat, reflections
from discord.ext import commands
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext

# Load environment variables
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Ensure tokens are loaded
if not DISCORD_TOKEN or not TELEGRAM_TOKEN:
    print("\u274C Error: One or more bot tokens are missing!")
    exit(1)
print(f"DISCORD_BOT_TOKEN: {DISCORD_TOKEN[:5]}...") 

# Define chatbot responses with case-insensitive regex patterns
pairs = [
    [r"(?i)\bhi\b|\bhello\b|\bhey\b", ["Hello! How can I assist you today?"]],
    
    [r"(?i)\bAPR\b|\bAutomatic Power Reduction\b|\bAPR alarm\b|\bresolve APR alarm\b", 
    ["This alarm occurs due to dirty ports. Clean the TX pigatil and Patch chord and FMS port and Pigatil, if still alarm persists then you need to clean device port, if still persists then you need to change patch chord."]],

    [r"(?i)\bOSC Los\b|\bOSCLOS\b|\bosc\b|\bOptical Line Fail\b|\bOptical Line Failed\b|\bOpticalLine\b|\bLD_Input\b|\bLD Input\b|\blos\b", 
    ["You need to check fiber where the fault is generally occurring. This usually happens due to fiber cuts."]],
    
    [r"(?i)\bPower Failure - A\b|\bPower Failure - B\b|\bPower\b", 
    ["This alarm is raised against a power feed when the shelf processor detects low or no voltage on the A or B backplane power feed."]],
    
    [r"(?i)\bShutoff Threshold Crossed\b|\bShutoff\b", 
    ["This alarm is raised against an AMP facility when the total input optical power to the amplifier has fallen below the provisioned Shutoff Threshold level."]],

    [r"(?i)\bhigh Received Span loss\b|\bSpan Loss\b|\bSpan\b", 
    ["Need to clear degradation, take OTDR and LSPM and check where the degradation is happening."]],

    [r"(?i)\bHigh Fiber Loss\b|\bHighFiber\b|\bHFL\b", 
    ["Check internal patching, clean port, and patch chord."]],

    [r"(?i)\b(.*)Circuit Pack Fail\b", 
    ["Kindly arrange FE at site with a spare card of the same PEC code. Perform Soft Reset, then Warm Reset from NOC, then take logs and JOJI. If the alarm persists, replace the card."]],

    [r"(?i)\bLow Orl\b|\bORL\b|\blow optical return loss at output\b", 
    ["This alarm is raised against an AMP. You need to clean the TX pigtail, patch chord, and device port."]],

    [r"(?i)\bbye\b|\bgoodbye\b", ["Goodbye! Have a great day!"]],

    [r"(?i)(.*)", ["I'm not sure about that. Please contact the support team."]]
]


chatbot = Chat(pairs, reflections)

# Flask setup
app = Flask(__name__)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/get", methods=["GET"])
def chatbot_response():
    user_message = request.args.get("msg")
    response = chatbot.respond(user_message)
    return response

# Telegram Bot setup
async def telegram_start(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text("Hello! I am your chatbot. How can I assist you?")

async def telegram_handle_message(update: Update, context: CallbackContext) -> None:
    user_text = update.message.text
    response = chatbot.respond(user_text)
    await update.message.reply_text(response)

async def run_telegram_bot():
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("start", telegram_start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, telegram_handle_message))
    print("\u2705 Telegram bot is running...")
    await application.initialize()
    await application.start()
    await application.updater.start_polling()

# Discord bot setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f'\u2705 Logged in as {bot.user}!')

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    response = chatbot.respond(message.content)
    await message.channel.send(response)
    await bot.process_commands(message)

# Run Flask in a separate thread
def run_flask():
    app.run(host="0.0.0.0", port=5000, use_reloader=False)

# Main function to run both Flask and bots concurrently
async def main():
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    await asyncio.gather(run_telegram_bot(), bot.start(DISCORD_TOKEN))

if __name__ == "__main__":
    asyncio.run(main())

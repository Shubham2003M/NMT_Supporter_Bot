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
...
@app.route("/get", methods=["GET"])
def chatbot_response():
    user_message = request.args.get("msg", "").strip().lower()

    def create_buttons(options):
        return '<br>'.join([f'<button onclick="sendMessage(\"{option}\")">{option}</button>' for option in options])

    if "step" not in session:
        session["step"] = "device"
        buttons = ["Ciena", "Huawei", "Muse", "Nokia PSS"]
        return f"👋 Welcome to the NMT Support Bot!<br>Please select your device:<br>{create_buttons(buttons)}"

    if session["step"] == "device":
        valid_devices = ["ciena", "huawei", "muse", "nokia pss"]
        if user_message in valid_devices:
            session["device"] = user_message
            session["step"] = "category"
            return f"✅ Device selected: {user_message.title()}<br>Choose alarm category:<br>{create_buttons(['Hardware', 'Fiber'])}"
        else:
            return f"❗ Please choose a valid device:<br>{create_buttons(['Ciena', 'Huawei', 'Muse', 'Nokia PSS'])}"

    elif session["step"] == "category":
        valid_categories = ["hardware", "fiber"]
        if user_message in valid_categories:
            session["category"] = user_message
            session["step"] = "alarm"
            alarms = list(ciena_alarms.get(user_message, {}).keys())
            return f"🔔 Please select an alarm:<br>{create_buttons(alarms)}"
        else:
            return f"❗ Please choose a valid category:<br>{create_buttons(['Hardware', 'Fiber'])}"

    elif session["step"] == "alarm":
        category = session.get("category")
        alarm_dict = ciena_alarms.get(category, {})
        selected_alarm = next((a for a in alarm_dict if user_message == a.lower()), None)
        if selected_alarm:
            session.clear()
            return alarm_dict[selected_alarm].replace('\n', '<br>')
        return f"❗ Alarm not recognized. Please try one from:<br>{create_buttons(list(alarm_dict.keys()))}"

    return "I'm not sure how to handle that."

# In your HTML template (index.html), ensure there's a JS function like this:
# function sendMessage(msg) {
#   document.getElementById('userInput').value = msg;
#   document.getElementById('sendBtn').click();
# }

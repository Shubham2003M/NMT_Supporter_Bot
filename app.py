import os
import asyncio
import threading
import discord
from flask import Flask, render_template, request, session
from dotenv import load_dotenv
from discord.ext import commands
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext

# Flask must be defined before use
app = Flask(__name__)
app.secret_key = "nmt_secret_key"

# Load environment variables
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# User session states
user_device_map = {}
user_alarm_category = {}

# Alarm data (include your ciena_alarms dictionary here)
ciena_alarms = {
    "hardware": {
        "Circuit Pack Failed": "Example resolution for Circuit Pack Failed.",
        "Circuit Pack Missing": "Example resolution for Circuit Pack Missing."
    },
    "fiber": {
        "High Fiber Loss": "Example resolution for High Fiber Loss.",
        "Optical Line Failed": "Example resolution for Optical Line Failed."
    }
}

@app.route("/")
def home():
    return render_template("index.html")

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

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    # Bind to 0.0.0.0 so Render can access it from outside the container
    app.run(host="0.0.0.0", port=port)


# Ensure your HTML template includes:
# <script>
# function sendMessage(msg) {
#   document.getElementById('userInput').value = msg;
#   document.getElementById('sendBtn').click();
# }
# </script>

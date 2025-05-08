import telebot
import requests
import json

# Ku buuxi token-yadaada halkan
TELEGRAM_BOT_TOKEN = "8018323716:AAFmGrW-LCBiW1oaJRAfQp-cuOwSu4r5nvc"
GEMINI_API_KEY = "AIzaSyAto78yGVZobxOwPXnl8wCE9ZW8Do2R8HA"

# Initialize bot
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)
bot.remove_webhook()  # si polling si sax ah u shaqeeyo

# Xasuusta: user_id -> list of messages
user_memory = {}

# ===== Gemini API =====
def ask_gemini(user_id, user_message):
    if user_id not in user_memory:
        user_memory[user_id] = []

    user_memory[user_id].append({"role": "user", "text": user_message})
    history = user_memory[user_id][-10:]
    parts = [{"text": msg["text"]} for msg in history]

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
    headers = {'Content-Type': 'application/json'}
    payload = {
        "contents": [{
            "parts": parts
        }]
    }

    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        result = response.json()

        if "candidates" in result:
            reply_text = result['candidates'][0]['content']['parts'][0]['text']
            user_memory[user_id].append({"role": "model", "text": reply_text})
            return reply_text
        else:
            return "Gemini API error: " + json.dumps(result)
    except Exception as e:
        return f"Qalad dhacay: {str(e)}"

# ===== Telegram Command Handlers =====
@bot.message_handler(commands=['start'])
def handle_start(message):
    bot.reply_to(message, "Waa salaaman tahay! Waxaan ahay AI bot ku shaqeeya Gemini. Fariin ii soo dir si aan kuu caawiyo.")

@bot.message_handler(commands=['reset'])
def reset_memory(message):
    user_id = message.from_user.id
    user_memory.pop(user_id, None)
    bot.reply_to(message, "Xasuusta waa la nadiifiyey. Waxaad bilaabi kartaa sheeko cusub.")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_id = message.from_user.id
    user_input = message.text
    reply = ask_gemini(user_id, user_input)
    bot.reply_to(message, reply)

# ===== Telegram Bot Setup (Commands, Description) =====
def set_bot_commands():
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/setMyCommands"
    commands = {
        "commands": [
            {"command": "start", "description": "Bilowga sheekada bot-ka"},
            {"command": "reset", "description": "Tirtir xasuusta sheekada"}
        ]
    }
    response = requests.post(url, json=commands)
    print("Commands response:", response.json())

def set_bot_description():
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/setMyDescription"
    payload = {
        "description": "Bot-kan wuxuu kuu oggolaanayaa inaad la sheekaysato Gemini AI si aad u hesho caawin iyo macluumaad degdeg ah."
    }
    response = requests.post(url, json=payload)
    print("Description response:", response.json())

def set_bot_short_description():
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/setMyShortDescription"
    payload = {
        "short_description": "Gemini AI Chat Bot"
    }
    response = requests.post(url, json=payload)
    print("Short Description response:", response.json())

# ===== Main App Entry Point =====
if __name__ == "__main__":
    set_bot_commands()
    set_bot_description()
    set_bot_short_description()
    print("Bot is running...")
    bot.polling()

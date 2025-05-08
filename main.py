import telebot
import requests
import json

# Ku beddel token-kaaga
TELEGRAM_BOT_TOKEN = "8018323716:AAFmGrW-LCBiW1oaJRAfQp-cuOwSu4r5nvc"
GEMINI_API_KEY = "AIzaSyAto78yGVZobxOwPXnl8wCE9ZW8Do2R8HA"

# Initialize bot
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

# Xasuusta: user_id -> list of messages
user_memory = {}

# Gemini API call
def ask_gemini(user_id, user_message):
    if user_id not in user_memory:
        user_memory[user_id] = []

    # Ku dar user message
    user_memory[user_id].append({"role": "user", "text": user_message})

    # Isticmaal max 10 ugu dambeysay
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
        reply_text = result['candidates'][0]['content']['parts'][0]['text']

        # Ku dar jawaabta AI
        user_memory[user_id].append({"role": "model", "text": reply_text})
        return reply_text
    except Exception as e:
        return f"Qalad dhacay: {str(e)}"

# Amar: /reset
@bot.message_handler(commands=['reset'])
def reset_memory(message):
    user_id = message.from_user.id
    user_memory.pop(user_id, None)
    bot.reply_to(message, "Xasuusta waa la nadiifiyey. Waxaad bilaabi kartaa sheeko cusub.")

# Fariin kasta: chat
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_id = message.from_user.id
    user_input = message.text

    reply = ask_gemini(user_id, user_input)
    bot.reply_to(message, reply)

bot.polling()

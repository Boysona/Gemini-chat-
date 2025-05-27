#!/usr/bin/env python3
import os
import json
import asyncio
import logging
import shutil
from flask import Flask, request, abort
from telebot import TeleBot, types
from msspeech import MSSpeech, MSSpeechError  # a_main import waa laga saaray

# ====== CONFIGURATION ======
BOT_TOKEN  = "7236852370:AAF7I0G4t6iQWX5vmkh2b8EnTCVgxuQZzPo"
BASE_URL   = "https://gemini-chat-53gz.onrender.com/"
AUDIO_DIR  = "audio_files"
USERS_DB   = "users.json"
VOICE_LIST = [
    "en-US-AriaNeural",
    "en-US-GuyNeural",
    "en-GB-LibbyNeural",
    "en-GB-RyanNeural",
    "so-SO-UbaxNeural",
    "so-SO-MuuseNeural",
    # … ku dar voice kale haddii loo baahdo …
]
# ===========================

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Flask & Bot init
app = Flask(__name__)
bot = TeleBot(BOT_TOKEN, threaded=False)

# Ensure dirs + users DB
os.makedirs(AUDIO_DIR, exist_ok=True)
if os.path.isfile(USERS_DB):
    with open(USERS_DB, "r") as f:
        users = json.load(f)
else:
    users = {}
    with open(USERS_DB, "w") as f:
        json.dump(users, f)

def save_users():
    with open(USERS_DB, "w") as f:
        json.dump(users, f, indent=2)

def get_user_voice(user_id):
    return users.get(str(user_id), VOICE_LIST[0])

def make_voice_keyboard():
    kb = types.InlineKeyboardMarkup(row_width=2)
    buttons = [
        types.InlineKeyboardButton(text=v, callback_data=f"voice|{v}")
        for v in VOICE_LIST
    ]
    kb.add(*buttons)
    return kb

# Qeexida a_main gudaha faylka
async def a_main(voice_name: str, text: str, filename: str,
                 rate: int = 0, pitch: int = 0, volume: float = 1.0) -> int:
    mss = MSSpeech()
    await mss.set_voice(voice_name)
    await mss.set_rate(rate)
    await mss.set_pitch(pitch)
    await mss.set_volume(volume)
    return await mss.synthesize(text, filename)

async def synth_and_send(chat_id, user_id, text):
    voice = get_user_voice(user_id)
    filename = os.path.join(AUDIO_DIR, f"{user_id}.mp3")
    try:
        await a_main(
            voice_name=voice,
            text=text,
            filename=filename,
            rate=0,
            pitch=0,
            volume=1.0
        )
        with open(filename, "rb") as f:
            bot.send_audio(chat_id, f, caption=f"Voice: {voice}")
    except MSSpeechError as e:
        bot.send_message(chat_id, f"❌ TTS Error: {e}")
    except Exception:
        logger.exception("Unexpected error")
        bot.send_message(chat_id, "❌ Internal error occurred.")

# ====== BOT HANDLERS ======

@bot.message_handler(commands=["start"])
def cmd_start(msg):
    bot.send_message(
        msg.chat.id,
        "👋 *Welcome!* Choose your TTS voice first:",
        parse_mode="Markdown",
        reply_markup=make_voice_keyboard()
    )

@bot.message_handler(commands=["change_voice"])
def cmd_change_voice(msg):
    bot.send_message(
        msg.chat.id,
        "🗣️ Select a new voice:",
        reply_markup=make_voice_keyboard()
    )

@bot.callback_query_handler(func=lambda c: c.data.startswith("voice|"))
def on_voice_select(call):
    _, voice = call.data.split("|", 1)
    users[str(call.from_user.id)] = voice
    save_users()
    bot.answer_callback_query(call.id, f"Voice set to {voice}")
    bot.send_message(
        call.message.chat.id,
        f"✅ Your voice is now *{voice}*",
        parse_mode="Markdown"
    )

@bot.message_handler(commands=["speak"])
def cmd_speak(msg):
    parts = msg.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.send_message(
            msg.chat.id,
            "Usage: `/speak <your text>`",
            parse_mode="Markdown"
        )
        return
    text = parts[1].strip()
    bot.send_chat_action(msg.chat.id, "record_audio")
    # Waa in async function la woco sidaan:
    asyncio.run(synth_and_send(msg.chat.id, msg.from_user.id, text))

@bot.message_handler(func=lambda m: True)
def fallback(msg):
    bot.send_message(
        msg.chat.id,
        "I didn't understand. Use /speak or /change_voice.",
        parse_mode="Markdown"
    )

# ====== WEBHOOK ROUTES ======

@app.route('/', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        update = types.Update.de_json(request.get_data().decode('utf-8'))
        bot.process_new_updates([update])
        return '', 200
    return abort(403)

@app.route('/set_webhook', methods=['GET', 'POST'])
def set_webhook():
    bot.delete_webhook()
    bot.set_webhook(url=BASE_URL)
    return f"Webhook set to {BASE_URL}", 200

@app.route('/delete_webhook', methods=['GET', 'POST'])
def delete_webhook():
    bot.delete_webhook()
    return 'Webhook deleted.', 200

# ====== APP ENTRYPOINT ======

if __name__ == "__main__":
    if os.path.exists(AUDIO_DIR):
        shutil.rmtree(AUDIO_DIR)
    os.makedirs(AUDIO_DIR, exist_ok=True)

    # Set webhook on start
    with app.test_request_context():
        bot.delete_webhook()
        bot.set_webhook(url=BASE_URL)

    port = int(os.environ.get('PORT', 8080))
    logger.info(f"Starting Flask on 0.0.0.0:{port}")
    app.run(host="0.0.0.0", port=port)

#!/usr/bin/env python3
import os
import json
import asyncio
import logging
import shutil
from flask import Flask, request, abort
from telebot import TeleBot, types
from msspeech import MSSpeech, MSSpeechError

# ====== CONFIG ======
BOT_TOKEN  = "7236852370:AAF7I0G4t6iQWX5vmkh2b8EnTCVgxuQZzPo"
BASE_URL   = "https://gemini-chat-53gz.onrender.com/"
AUDIO_DIR  = "audio_files"
USERS_DB   = "users.json"
VOICE_LIST = [
    "en-US-AriaNeural","en-US-GuyNeural",
    "en-GB-LibbyNeural","en-GB-RyanNeural",
    "so-SO-UbaxNeural","so-SO-MuuseNeural",
]
# ==================

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
bot = TeleBot(BOT_TOKEN, threaded=False)

os.makedirs(AUDIO_DIR, exist_ok=True)
if os.path.isfile(USERS_DB):
    users = json.load(open(USERS_DB))
else:
    users = {}
    json.dump(users, open(USERS_DB, "w"), indent=2)

def save_users():
    json.dump(users, open(USERS_DB, "w"), indent=2)

def get_user_voice(uid): return users.get(str(uid), VOICE_LIST[0])

def make_voice_keyboard():
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(*[types.InlineKeyboardButton(v, callback_data=f"voice|{v}") for v in VOICE_LIST])
    return kb

# async helper
async def a_main(voice, text, filename, rate=0, pitch=0, volume=1.0):
    mss = MSSpeech()
    await mss.set_voice(voice)
    await mss.set_rate(rate)
    await mss.set_pitch(pitch)
    await mss.set_volume(volume)
    return await mss.synthesize(text, filename)

async def synth_and_send(chat_id, user_id, text):
    voice = get_user_voice(user_id)
    filename = os.path.join(AUDIO_DIR, f"{user_id}.mp3")
    logger.info(f"Starting synthesis for user {user_id} with voice {voice}")
    try:
        bytes_written = await a_main(voice, text, filename)
        logger.info(f"Synthesized {bytes_written} bytes to {filename}")
    except MSSpeechError as e:
        logger.error(f"TTS Error: {e}")
        bot.send_message(chat_id, f"❌ TTS Error: {e}")
        return
    except Exception as e:
        logger.exception("Unexpected during synthesis")
        bot.send_message(chat_id, "❌ Internal error occurred.")
        return

    # Debug: did the file actually get created?
    if not os.path.isfile(filename) or os.path.getsize(filename) == 0:
        logger.error("MP3 file missing or empty")
        bot.send_message(chat_id, "❌ Error: MP3 file not found or empty.")
        return

    # Tell Telegram we're uploading
    bot.send_chat_action(chat_id, "upload_audio")
    with open(filename, "rb") as f:
        bot.send_audio(chat_id, f, caption=f"Voice: {voice}")

# ====== HANDLERS ======

@bot.message_handler(commands=["start"])
def cmd_start(m):
    bot.send_message(m.chat.id, "👋 *Welcome!* Choose your TTS voice:", parse_mode="Markdown", reply_markup=make_voice_keyboard())

@bot.message_handler(commands=["change_voice"])
def cmd_change_voice(m):
    bot.send_message(m.chat.id, "🗣️ Select a new voice:", reply_markup=make_voice_keyboard())

@bot.callback_query_handler(lambda c: c.data.startswith("voice|"))
def on_voice(c):
    _, v = c.data.split("|",1)
    users[str(c.from_user.id)] = v
    save_users()
    bot.answer_callback_query(c.id, f"Voice set to {v}")
    bot.send_message(c.message.chat.id, f"✅ Voice is now *{v}*", parse_mode="Markdown")

@bot.message_handler(commands=["speak"])
def cmd_speak(m):
    parts = m.text.split(maxsplit=1)
    if len(parts)<2:
        return bot.send_message(m.chat.id, "Usage: `/speak <text>`", parse_mode="Markdown")
    text = parts[1].strip()
    # Run synthesis
    asyncio.run(synth_and_send(m.chat.id, m.from_user.id, text))

@bot.message_handler(func=lambda m: True)
def fallback(m):
    bot.send_message(m.chat.id, "I didn't understand. Use /speak or /change_voice.", parse_mode="Markdown")

# ====== WEBHOOK ======

@app.route('/', methods=['POST'])
def webhook():
    if request.headers.get('content-type')=='application/json':
        upd = types.Update.de_json(request.get_data().decode(), request.app)
        bot.process_new_updates([upd])
        return '',200
    return abort(403)

@app.route('/set_webhook', methods=['GET','POST'])
def set_webhook():
    bot.delete_webhook()
    bot.set_webhook(url=BASE_URL)
    return f"Webhook set to {BASE_URL}",200

@app.route('/delete_webhook', methods=['GET','POST'])
def del_webhook():
    bot.delete_webhook()
    return 'Webhook deleted',200

# ====== MAIN ======

if __name__=="__main__":
    if os.path.exists(AUDIO_DIR): shutil.rmtree(AUDIO_DIR)
    os.makedirs(AUDIO_DIR, exist_ok=True)
    # ensure webhook
    with app.test_request_context():
        bot.delete_webhook()
        bot.set_webhook(url=BASE_URL)
    port = int(os.environ.get("PORT",8080))
    app.run(host="0.0.0.0", port=port)


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
logger = logging.getLogger("tts-bot")

app = Flask(__name__)
bot = TeleBot(BOT_TOKEN, threaded=False)

os.makedirs(AUDIO_DIR, exist_ok=True)
users = {}

if os.path.exists(USERS_DB):
    with open(USERS_DB, "r") as f:
        users = json.load(f)

def save_users():
    with open(USERS_DB, "w") as f:
        json.dump(users, f, indent=2)

def get_user_voice(uid):
    return users.get(str(uid), VOICE_LIST[0])

def make_voice_keyboard():
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(*[types.InlineKeyboardButton(v, callback_data=f"voice|{v}") for v in VOICE_LIST])
    return kb

# ====== TEXT-TO-SPEECH ======
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

    try:
        bot.send_chat_action(chat_id, "record_audio")
        await a_main(voice, text, filename)
        if not os.path.exists(filename) or os.path.getsize(filename) == 0:
            bot.send_message(chat_id, "❌ MP3 file not generated or empty.")
            return

        with open(filename, "rb") as f:
            bot.send_audio(chat_id, f, caption=f"🎤 Voice: {voice}")
    except MSSpeechError as e:
        bot.send_message(chat_id, f"❌ MSSpeech error: {e}")
    except Exception as e:
        logger.exception("TTS error")
        bot.send_message(chat_id, "❌ Unexpected error occurred.")

# ====== COMMAND HANDLERS ======
@bot.message_handler(commands=["start"])
def cmd_start(m):
    bot.send_message(m.chat.id, "👋 Welcome! Use /speak or choose voice:", reply_markup=make_voice_keyboard())

@bot.message_handler(commands=["change_voice"])
def cmd_change_voice(m):
    bot.send_message(m.chat.id, "🎙️ Choose a voice:", reply_markup=make_voice_keyboard())

@bot.callback_query_handler(lambda c: c.data.startswith("voice|"))
def on_voice_change(c):
    _, voice = c.data.split("|", 1)
    users[str(c.from_user.id)] = voice
    save_users()
    bot.answer_callback_query(c.id, f"✔️ Voice changed to {voice}")
    bot.send_message(c.message.chat.id, f"🔊 Now using: *{voice}*", parse_mode="Markdown")

@bot.message_handler(commands=["speak"])
def cmd_speak(m):
    parts = m.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.send_message(m.chat.id, "❗ Usage: `/speak <text>`", parse_mode="Markdown")
        return
    text = parts[1]
    asyncio.run(synth_and_send(m.chat.id, m.from_user.id, text))

@bot.message_handler(func=lambda m: True)
def fallback(m):
    bot.send_message(m.chat.id, "🤖 Use /speak or /change_voice")

# ====== WEBHOOK INTEGRATION ======
@app.route('/', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return '', 200
    return abort(403)

@app.route('/set_webhook', methods=['GET'])
def set_webhook():
    success = bot.set_webhook(url=BASE_URL)
    return f"Webhook set: {success}", 200

@app.route('/delete_webhook', methods=['GET'])
def delete_webhook():
    bot.delete_webhook()
    return "Webhook deleted", 200

# ====== APP RUNNER ======
if __name__ == "__main__":
    shutil.rmtree(AUDIO_DIR, ignore_errors=True)
    os.makedirs(AUDIO_DIR, exist_ok=True)

    with app.test_request_context():
        bot.delete_webhook()
        bot.set_webhook(url=BASE_URL)

    port = int(os.environ.get("PORT", 8080))
    logger.info(f"Bot running on port {port}")
    app.run(host="0.0.0.0", port=port)

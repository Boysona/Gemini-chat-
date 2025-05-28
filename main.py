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

# Define your voices grouped by language code
VOICE_GROUPS = {
    "English 🇬🇧": [
        "en-US-AriaNeural", "en-US-GuyNeural",
        "en-GB-LibbyNeural", "en-GB-RyanNeural",
    ],
    "Somali 🇸🇴": [
        "so-SO-UbaxNeural", "so-SO-MuuseNeural",
    ],
}
# Flattened list for default
VOICE_LIST = sum(VOICE_GROUPS.values(), [])
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
    # default to first voice in VOICE_LIST
    return users.get(str(uid), VOICE_LIST[0])

# ─── KEYBOARDS ────────────────────────────────────────────────────────────────

def make_language_keyboard() -> types.InlineKeyboardMarkup:
    """
    First level: show languages
    """
    kb = types.InlineKeyboardMarkup(row_width=1)
    for lang in VOICE_GROUPS:
        # callback_data: "lang|English 🇬🇧"
        kb.add(types.InlineKeyboardButton(lang, callback_data=f"lang|{lang}"))
    return kb

def make_voices_keyboard(lang: str) -> types.InlineKeyboardMarkup:
    """
    Second level: show voices for a given language
    """
    kb = types.InlineKeyboardMarkup(row_width=2)
    for voice in VOICE_GROUPS.get(lang, []):
        # callback_data: "voice|en-US-AriaNeural"
        kb.add(types.InlineKeyboardButton(voice, callback_data=f"voice|{voice}"))
    # add a back button to choose another language
    kb.add(types.InlineKeyboardButton("🔙 Back", callback_data="back_to_lang"))
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
    # 1) Welcome message with first name
    first = m.from_user.first_name or "there"
    welcome = (
        f"👋 Welcome, {first}!\n\n"
        "I’m your voice assistant bot. I can help you convert text into speech in different languages.\n"
        "Use the buttons below to get started!"
    )
    bot.send_message(m.chat.id, welcome)
    # 2) Show language buttons
    bot.send_message(m.chat.id, "🎙️ Choose a language:", reply_markup=make_language_keyboard())

@bot.message_handler(commands=["change_voice"])
def cmd_change_voice(m):
    bot.send_message(m.chat.id, "🎙️ Choose a language:", reply_markup=make_language_keyboard())

# Handle callback when tapping a language
@bot.callback_query_handler(lambda c: c.data.startswith("lang|") or c.data == "back_to_lang")
def on_language_select(c):
    data = c.data
    if data == "back_to_lang":
        bot.edit_message_text(
            "🎙️ Choose a language:",
            chat_id=c.message.chat.id,
            message_id=c.message.message_id,
            reply_markup=make_language_keyboard()
        )
    else:
        _, lang = data.split("|", 1)
        bot.edit_message_text(
            f"🎙️ Voices available for *{lang}*: ",
            chat_id=c.message.chat.id,
            message_id=c.message.message_id,
            parse_mode="Markdown",
            reply_markup=make_voices_keyboard(lang)
        )
    bot.answer_callback_query(c.id)

# Handle callback when tapping a specific voice
@bot.callback_query_handler(lambda c: c.data.startswith("voice|"))
def on_voice_change(c):
    _, voice = c.data.split("|", 1)
    users[str(c.from_user.id)] = voice
    save_users()
    bot.answer_callback_query(c.id, f"✔️ Voice changed to {voice}")
    # update the message to confirm
    bot.edit_message_caption(
        caption=f"🔊 Now using: *{voice}*",
        chat_id=c.message.chat.id,
        message_id=c.message.message_id,
        parse_mode="Markdown"
    )

# ====== MESSAGE HANDLING ======

@bot.message_handler(func=lambda m: True)
def handle_text(m):
    """
    Any plain text is immediately synthesized—no /speak needed.
    """
    text = m.text.strip()
    if not text:
        return
    # run TTS
    asyncio.run(synth_and_send(m.chat.id, m.from_user.id, text))

# ====== WEBHOOK INTEGRATION ======

@app.route('/', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        update = types.Update.de_json(request.get_data().decode('utf-8'))
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

    # ensure webhook is cleanly reset on start
    with app.test_request_context():
        bot.delete_webhook()
        bot.set_webhook(url=BASE_URL)

    port = int(os.environ.get("PORT", 8080))
    logger.info(f"Bot running on port {port}")
    app.run(host="0.0.0.0", port=port)

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

# Group voices by language for better organization
VOICES_BY_LANGUAGE = {
    "English 🇬🇧": [
        "en-US-AriaNeural", "en-US-GuyNeural",
        "en-GB-LibbyNeural", "en-GB-RyanNeural",
    ],
    "Somali 🇸🇴": [
        "so-SO-UbaxNeural", "so-SO-MuuseNeural",
    ]
}
# ==================

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("tts-bot")

app = Flask(__name__)
bot = TeleBot(BOT_TOKEN, threaded=False)

os.makedirs(AUDIO_DIR, exist_ok=True)
users = {}

if os.path.exists(USERS_DB):
    try:
        with open(USERS_DB, "r") as f:
            users = json.load(f)
    except json.JSONDecodeError:
        logger.warning(f"Error decoding JSON from {USERS_DB}. Starting with empty users.")
        users = {}

def save_users():
    with open(USERS_DB, "w") as f:
        json.dump(users, f, indent=2)

def get_user_voice(uid):
    # Default to a specific voice if not found in user settings
    return users.get(str(uid), "en-US-AriaNeural")

def make_language_keyboard():
    kb = types.InlineKeyboardMarkup(row_width=1)
    for lang_name in VOICES_BY_LANGUAGE.keys():
        kb.add(types.InlineKeyboardButton(lang_name, callback_data=f"lang|{lang_name}"))
    return kb

def make_voice_keyboard_for_language(lang_name):
    kb = types.InlineKeyboardMarkup(row_width=2)
    voices = VOICES_BY_LANGUAGE.get(lang_name, [])
    for voice in voices:
        kb.add(types.InlineKeyboardButton(voice, callback_data=f"voice|{voice}"))
    kb.add(types.InlineKeyboardButton("⬅️ Back to Languages", callback_data="back_to_languages"))
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
            bot.send_message(chat_id, "❌ MP3 file not generated or empty. Please try again.")
            return

        with open(filename, "rb") as f:
            bot.send_audio(chat_id, f, caption=f"🎤 Voice: {voice}")
    except MSSpeechError as e:
        bot.send_message(chat_id, f"❌ Wuu jiraa khalad dhinaca codka ah: {e}")
    except Exception as e:
        logger.exception("TTS error")
        bot.send_message(chat_id, "❌ Wuxuu dhacay khalad aan la filayn. Fadlan isku day mar kale.")
    finally:
        if os.path.exists(filename):
            os.remove(filename) # Clean up the audio file

# ====== COMMAND HANDLERS ======
@bot.message_handler(commands=["start"])
def cmd_start(m):
    first_name = m.from_user.first_name if m.from_user.first_name else "friend"
    welcome_message = (
        f"Welcome, {first_name}! 👋\n"
        "I’m your voice assistant bot. I can help you convert text into speech in different languages. "
        "Use /change_voice to get started!"
    )
    bot.send_message(m.chat.id, welcome_message)

@bot.message_handler(commands=["change_voice"])
def cmd_change_voice(m):
    bot.send_message(m.chat.id, "🎙️ Choose a language:", reply_markup=make_language_keyboard())

@bot.callback_query_handler(lambda c: c.data.startswith("lang|"))
def on_language_select(c):
    _, lang_name = c.data.split("|", 1)
    bot.edit_message_text(
        chat_id=c.message.chat.id,
        message_id=c.message.message_id,
        text=f"🎙️ Choose a voice for {lang_name}:",
        reply_markup=make_voice_keyboard_for_language(lang_name)
    )
    bot.answer_callback_query(c.id)

@bot.callback_query_handler(lambda c: c.data.startswith("voice|"))
def on_voice_change(c):
    _, voice = c.data.split("|", 1)
    users[str(c.from_user.id)] = voice
    save_users()
    bot.answer_callback_query(c.id, f"✔️ Voice changed to {voice}")
    bot.edit_message_text(
        chat_id=c.message.chat.id,
        message_id=c.message.message_id,
        text=f"🔊 Hadda waxaad isticmaalaysaa: *{voice}*. Waxaad bilaabi kartaa inaad qorto qoraalka.",
        parse_mode="Markdown"
    )

@bot.callback_query_handler(lambda c: c.data == "back_to_languages")
def on_back_to_languages(c):
    bot.edit_message_text(
        chat_id=c.message.chat.id,
        message_id=c.message.message_id,
        text="🎙️ Choose a language:",
        reply_markup=make_language_keyboard()
    )
    bot.answer_callback_query(c.id)

@bot.message_handler(func=lambda m: True)
def handle_text_messages(m):
    # Only process text messages that are not commands
    if m.text and not m.text.startswith('/'):
        asyncio.run(synth_and_send(m.chat.id, m.from_user.id, m.text))
    else:
        bot.send_message(m.chat.id, "Waxaan fahmay, fadlan isticmaal `/start` ama `/change_voice`.")


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

    # These lines are for local testing/setup, ensure they are run before deployment
    # For Render deployment, webhooks are typically managed by the platform config or a separate script.
    # bot.delete_webhook()
    # bot.set_webhook(url=BASE_URL)

    port = int(os.environ.get("PORT", 8080))
    logger.info(f"Bot running on port {port}")
    app.run(host="0.0.0.0", port=port)

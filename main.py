
import os
import json
import asyncio
import logging
from telebot import TeleBot, types
from msspeech import MSSpeech, MSSpeechError, a_main

# ====== CONFIGURATION ======
BOT_TOKEN    = os.getenv("7236852370:AAF7I0G4t6iQWX5vmkh2b8EnTCVgxuQZzPo")
AUDIO_DIR    = "audio_files"
USERS_DB     = "users.json"
VOICE_LIST   = [
    "en-US-AriaNeural",
    "en-US-GuyNeural",
    "en-GB-LibbyNeural",
    "en-GB-RyanNeural",
    "so-SO-UbaxNeural",
    "so-SO-MuuseNeural",
    # … ku dar voice kale sida aad rabto …
]
# ===========================

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = TeleBot(BOT_TOKEN)
os.makedirs(AUDIO_DIR, exist_ok=True)

# Load or init users DB
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

# ====== HELPERS ======

def make_voice_keyboard():
    kb = types.InlineKeyboardMarkup(row_width=2)
    buttons = [
        types.InlineKeyboardButton(text=v, callback_data=f"voice|{v}")
        for v in VOICE_LIST
    ]
    kb.add(*buttons)
    return kb

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
    except Exception as e:
        logger.exception("Unexpected error")
        bot.send_message(chat_id, "❌ Internal error occurred.")

# ====== COMMANDS ======

@bot.message_handler(commands=["start"])
def cmd_start(msg):
    uid = msg.from_user.id
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
    bot.send_message(call.message.chat.id, f"✅ Your voice is now *{voice}*", parse_mode="Markdown")

@bot.message_handler(commands=["speak"])
def cmd_speak(msg):
    parts = msg.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.send_message(msg.chat.id, "Usage: `/speak <your text>`", parse_mode="Markdown")
        return
    text = parts[1].strip()
    bot.send_chat_action(msg.chat.id, "record_audio")
    # run synth in background
    asyncio.run(synth_and_send(msg.chat.id, msg.from_user.id, text))

@bot.message_handler(func=lambda m: True)
def fallback(msg):
    bot.send_message(
        msg.chat.id,
        "I didn't understand. Use /speak or /change_voice.",
        parse_mode="Markdown"
    )

if __name__ == "__main__":
    logger.info("Bot is up. Polling...")
    bot.polling(none_stop=True)

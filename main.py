import os
import json
import asyncio
import logging
import shutil
from flask import Flask, request, abort
from telebot import TeleBot, types
from msspeech import MSSpeech, MSSpeechError

# ====== CONFIG ======
BOT_TOKEN  = "8114722716:AAHayxlSflH42TzI7ofnaWU99dMwc4NXt8Q"
BASE_URL   = "https://gemini-chat-0a7l.onrender.com/"
AUDIO_DIR  = "audio_files"
USERS_DB   = "users.json"

# Group voices by language for better organization

VOICES_BY_LANGUAGE = {
    "English 🇬🇧": [
        "en-US-AriaNeural", "en-US-GuyNeural", "en-US-JennyNeural", "en-US-DavisNeural",
        "en-GB-LibbyNeural", "en-GB-RyanNeural", "en-GB-MiaNeural", "en-GB-ThomasNeural",
        "en-AU-NatashaNeural", "en-AU-WilliamNeural", "en-CA-LindaNeural", "en-CA-ClaraNeural",
        "en-IE-EmilyNeural", "en-IE-ConnorNeural", "en-IN-NeerjaNeural", "en-IN-PrabhatNeural"
    ],
    "Somali 🇸🇴": [
        "so-SO-UbaxNeural", "so-SO-MuuseNeural",
    ],
    "Arabic 🇸🇦": [
        "ar-SA-HamedNeural", "ar-SA-ZariyahNeural", "ar-EG-SalmaNeural", "ar-EG-ShakirNeural",
        "ar-DZ-AminaNeural", "ar-DZ-IsmaelNeural", "ar-BH-LailaNeural", "ar-BH-AliNeural",
        "ar-IQ-RanaNeural", "ar-IQ-BasselNeural", "ar-KW-FahedNeural", "ar-KW-NouraNeural",
        "ar-OM-AishaNeural", "ar-OM-SamirNeural", "ar-QA-MoazNeural", "ar-QA-ZainabNeural",
        "ar-SY-AmiraNeural", "ar-SY-LaithNeural", "ar-AE-FatimaNeural", "ar-AE-HamdanNeural",
        "ar-YE-HamdanNeural", "ar-YE-SarimNeural"
    ],
    "Spanish 🇪🇸": [
        "es-ES-AlvaroNeural", "es-ES-ElviraNeural", "es-MX-DaliaNeural", "es-MX-JorgeNeural",
        "es-AR-ElenaNeural", "es-AR-TomasNeural", "es-CO-SalomeNeural", "es-CO-GonzaloNeural",
        "es-US-PalomaNeural", "es-US-JuanNeural", "es-CL-LorenzoNeural", "es-CL-CatalinaNeural",
        "es-PE-CamilaNeural", "es-PE-DiegoNeural", "es-VE-PaolaNeural", "es-VE-SebastianNeural",
        "es-CR-MariaNeural", "es-CR-JuanNeural", "es-DO-RamonaNeural", "es-DO-AntonioNeural"
    ],
    "French 🇫🇷": [
        "fr-FR-DeniseNeural", "fr-FR-HenriNeural", "fr-CA-SylvieNeural", "fr-CA-JeanNeural",
        "fr-CH-ArianeNeural", "fr-CH-FabriceNeural", "fr-BE-CharlineNeural", "fr-BE-CamilleNeural"
    ],
    "German 🇩🇪": [
        "de-DE-KatjaNeural", "de-DE-ConradNeural", "de-CH-LeniNeural", "de-CH-JanNeural",
        "de-AT-IngridNeural", "de-AT-JonasNeural"
    ],
    "Chinese 🇨🇳": [
        "zh-CN-XiaoxiaoNeural", "zh-CN-YunyangNeural", "zh-CN-YunjianNeural", "zh-CN-XiaoyunNeural",
        "zh-TW-HsiaoChenNeural", "zh-TW-YunJheNeural", "zh-HK-HiuMaanNeural", "zh-HK-WanLungNeural",
        "zh-SG-XiaoMinNeural", "zh-SG-YunJianNeural"
    ],
    "Japanese 🇯🇵": [
        "ja-JP-NanamiNeural", "ja-JP-KeitaNeural", "ja-JP-MayuNeural", "ja-JP-DaichiNeural"
    ],
    "Portuguese 🇧🇷": [
        "pt-BR-FranciscaNeural", "pt-BR-AntonioNeural", "pt-PT-RaquelNeural", "pt-PT-DuarteNeural"
    ],
    "Russian 🇷🇺": [
        "ru-RU-SvetlanaNeural", "ru-RU-DmitryNeural", "ru-RU-LarisaNeural", "ru-RU-MaximNeural"
    ],
    "Hindi 🇮🇳": [
        "hi-IN-SwaraNeural", "hi-IN-MadhurNeural"
    ],
    "Turkish 🇹🇷": [
        "tr-TR-EmelNeural", "tr-TR-AhmetNeural"
    ],
    "Korean 🇰🇷": [
        "ko-KR-SunHiNeural", "ko-KR-InJoonNeural"
    ],
    "Italian 🇮🇹": [
        "it-IT-ElsaNeural", "it-IT-DiegoNeural"
    ],
    "Indonesian 🇮🇩": [
        "id-ID-GadisNeural", "id-ID-ArdiNeural"
    ],
    "Vietnamese 🇻🇳": [
        "vi-VN-HoaiMyNeural", "vi-VN-NamMinhNeural"
    ],
    "Thai 🇹🇭": [
        "th-TH-PremwadeeNeural", "th-TH-NiwatNeural"
    ],
    "Dutch 🇳🇱": [
        "nl-NL-ColetteNeural", "nl-NL-MaartenNeural"
    ],
    "Polish 🇵🇱": [
        "pl-PL-ZofiaNeural", "pl-PL-MarekNeural"
    ],
    "Swedish 🇸🇪": [
        "sv-SE-SofieNeural", "sv-SE-MattiasNeural"
    ],
    "Filipino 🇵🇭": [
        "fil-PH-BlessicaNeural", "fil-PH-AngeloNeural"
    ],
    "Greek 🇬🇷": [
        "el-GR-AthinaNeural", "el-GR-NestorasNeural"
    ],
    "Hebrew 🇮🇱": [
        "he-IL-AvriNeural", "he-IL-HilaNeural"
    ],
    "Hungarian 🇭🇺": [
        "hu-HU-NoemiNeural", "hu-HU-AndrasNeural"
    ],
    "Czech 🇨🇿": [
        "cs-CZ-VlastaNeural", "cs-CZ-AntoninNeural"
    ],
    "Danish 🇩🇰": [
        "da-DK-ChristelNeural", "da-DK-JeppeNeural"
    ],
    "Finnish 🇫🇮": [
        "fi-FI-SelmaNeural", "fi-FI-HarriNeural"
    ],
    "Norwegian 🇳🇴": [
        "nb-NO-PernilleNeural", "nb-NO-FinnNeural"
    ],
    "Romanian 🇷🇴": [
        "ro-RO-AlinaNeural", "ro-RO-EmilNeural"
    ],
    "Slovak 🇸🇰": [
        "sk-SK-LukasNeural", "sk-SK-ViktoriaNeural"
    ],
    "Ukrainian 🇺🇦": [
        "uk-UA-PolinaNeural", "uk-UA-OstapNeural"
    ],
    "Malay 🇲🇾": [
        "ms-MY-YasminNeural", "ms-MY-OsmanNeural"
    ],
    "Bengali 🇧🇩": [
        "bn-BD-NabanitaNeural", "bn-BD-BasharNeural"
    ],
    "Tamil 🇮🇳": [
        "ta-IN-PallaviNeural", "ta-IN-ValluvarNeural"
    ],
    "Telugu 🇮🇳": [
        "te-IN-ShrutiNeural", "te-IN-RagavNeural"
    ],
    "Kannada 🇮🇳": [
        "kn-IN-SapnaNeural", "kn-IN-GaneshNeural"
    ],
    "Malayalam 🇮🇳": [
        "ml-IN-SobhanaNeural", "ml-IN-MidhunNeural"
    ],
    "Gujarati 🇮🇳": [
        "gu-IN-DhwaniNeural", "gu-IN-AvinashNeural"
    ],
    "Marathi 🇮🇳": [
        "mr-IN-AarohiNeural", "mr-IN-ManoharNeural"
    ],
    "Urdu 🇵🇰": [
        "ur-PK-AsmaNeural", "ur-PK-FaizanNeural"
    ],
    "Nepali 🇳🇵": [
        "ne-NP-SaritaNeural", "ne-NP-AbhisekhNeural"
    ],
    "Sinhala 🇱🇰": [
        "si-LK-SameeraNeural", "si-LK-ThiliniNeural"
    ],
    "Khmer 🇰🇭": [
        "km-KH-SreymomNeural", "km-KH-PannNeural"
    ],
    "Lao 🇱🇦": [
        "lo-LA-ChanthavongNeural", "lo-LA-KeomanyNeural"
    ],
    "Myanmar 🇲🇲": [
        "my-MM-NilarNeural", "my-MM-ThihaNeural"
    ],
    "Georgian 🇬🇪": [
        "ka-GE-EkaNeural", "ka-GE-GiorgiNeural"
    ],
    "Armenian 🇦🇲": [
        "hy-AM-AnahitNeural", "hy-AM-AraratNeural"
    ],
    "Azerbaijani 🇦🇿": [
        "az-AZ-BabekNeural", "az-AZ-BanuNeural"
    ],
    "Kazakh 🇰🇿": [
        "kk-KZ-AigulNeural", "kk-KZ-NurzhanNeural"
    ],
    "Uzbek 🇺🇿": [
        "uz-UZ-MadinaNeural", "uz-UZ-SuhrobNeural"
    ],
    "Serbian 🇷🇸": [
        "sr-RS-NikolaNeural", "sr-RS-SophieNeural"
    ],
    "Croatian 🇭🇷": [
        "hr-HR-GabrijelaNeural", "hr-HR-SreckoNeural"
    ],
    "Slovenian 🇸🇮": [
        "sl-SI-PetraNeural", "sl-SI-RokNeural"
    ],
    "Latvian 🇱🇻": [
        "lv-LV-EveritaNeural", "lv-LV-AnsisNeural"
    ],
    "Lithuanian 🇱🇹": [
        "lt-LT-OnaNeural", "lt-LT-LeonasNeural"
    ],
    "Estonian 🇪🇪": [
        "et-EE-LiisNeural", "et-EE-ErkiNeural"
    ],
    "Amharic 🇪🇹": [
        "am-ET-MekdesNeural", "am-ET-AbebeNeural"
    ],
    "Swahili 🇰🇪": [
        "sw-KE-ZuriNeural", "sw-KE-RafikiNeural"
    ],
    "Zulu 🇿🇦": [
        "zu-ZA-ThandoNeural", "zu-ZA-ThembaNeural"
    ],
    "Xhosa 🇿🇦": [
        "xh-ZA-NomusaNeural", "xh-ZA-DumisaNeural"
    ],
    "Afrikaans 🇿🇦": [
        "af-ZA-AdriNeural", "af-ZA-WillemNeural"
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

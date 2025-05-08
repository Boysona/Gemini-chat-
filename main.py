import telebot
import google.generativeai as genai

# Replace with your actual Telegram Bot Token
TELEGRAM_BOT_TOKEN = "8018323716:AAFmGrW-LCBiW1oaJRAfQp-cuOwSu4r5nvc"

# Replace with your actual Google Gemini API Key
GOOGLE_GEMINI_API_KEY = "AIzaSyAto78yGVZobxOwPXnl8wCE9ZW8Do2R8HA"

# Initialize Telegram Bot
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

# Configure Google Gemini API
genai.configure(api_key=GOOGLE_GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-pro')

@bot.message_handler(commands=['start', 'hello'])
def send_welcome(message):
    bot.reply_to(message, "Hello! I am your AI chatbot powered by Gemini. Ask me anything!")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    try:
        response = model.generate_content(message.text)
        bot.reply_to(message, response.text)
    except Exception as e:
        bot.reply_to(message, f"Sorry, I encountered an error: {e}")

if __name__ == '__main__':
    print("Bot is running...")
    bot.polling(none_stop=True)

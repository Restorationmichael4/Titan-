import os
import logging
import requests
import schedule
import time
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, filters, CallbackContext
from flask import Flask
from threading import Thread

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

# Telegram Bot Token, Group ID, Channel Link from .env
TOKEN = os.getenv("TELEGRAM_TOKEN")
GROUP_ID = os.getenv("GROUP_ID")
CHANNEL_LINK = os.getenv("CHANNEL_LINK")

# Initialize personal finance data
finance_data = {"income": 0, "expenses": 0}

# Initialize Flask app for Render deployment
app = Flask(__name__)

# Helper function to send messages to the group
def send_confession_to_group(confession: str):
    """Send anonymous confession to the Telegram group."""
    updater = Updater(TOKEN, use_context=True)
    chat_id = GROUP_ID
    updater.bot.send_message(chat_id=chat_id, text=confession)

# Helper function to check if user joined the channel
def check_channel_member(update: Update) -> bool:
    """Check if the user has joined the channel."""
    try:
        user_id = update.message.from_user.id
        member = update.bot.get_chat_member(CHANNEL_LINK, user_id)
        return member.status in ['member', 'administrator', 'creator']
    except Exception as e:
        logger.error(f"Error checking channel membership: {e}")
        return False

# Command Handlers

def start(update: Update, context: CallbackContext):
    """Start command."""
    if not check_channel_member(update):
        update.message.reply_text(f"Please join the channel first: {CHANNEL_LINK}")
        return

    update.message.reply_text("Welcome to Super Bot! Choose a feature: /quiz, /finance, /study, /weather, /music, /fitness, /language, /confession")

def confession(update: Update, context: CallbackContext):
    """Receive anonymous confession and send it to the group."""
    if not check_channel_member(update):
        update.message.reply_text(f"Please join the channel first: {CHANNEL_LINK}")
        return

    confession_text = " ".join(context.args)
    
    if confession_text:
        send_confession_to_group(confession_text)
        update.message.reply_text("Your confession has been sent anonymously!")
    else:
        update.message.reply_text("Please provide a confession after the command.")

# Trivia/Quiz Command Handler
def quiz(update: Update, context: CallbackContext):
    """Trivia/Quiz using Open Trivia Database API."""
    if not check_channel_member(update):
        update.message.reply_text(f"Please join the channel first: {CHANNEL_LINK}")
        return

    url = "https://opentdb.com/api.php?amount=1&type=multiple"
    response = requests.get(url)
    question_data = response.json()
    question = question_data["results"][0]
    question_text = question["question"]
    options = question["incorrect_answers"] + [question["correct_answer"]]
    correct_answer = question["correct_answer"]

    # Shuffle options to randomize the answers
    import random
    random.shuffle(options)

    # Send question and options to user
    update.message.reply_text(f"Question: {question_text}\nOptions: {', '.join(options)}")

    # Store correct answer for the next step
    context.user_data["correct_answer"] = correct_answer

def check_answer(update: Update, context: CallbackContext):
    """Check if the user's answer is correct."""
    user_answer = update.message.text
    correct_answer = context.user_data.get("correct_answer")

    if user_answer.lower() == correct_answer.lower():
        update.message.reply_text("Correct!")
    else:
        update.message.reply_text(f"Incorrect! The correct answer was: {correct_answer}")

# Personal Finance Command Handlers
def finance(update: Update, context: CallbackContext):
    """Log income and expenses."""
    if not check_channel_member(update):
        update.message.reply_text(f"Please join the channel first: {CHANNEL_LINK}")
        return

    command = " ".join(context.args).lower()
    
    if command.startswith("income"):
        try:
            amount = float(command.split(" ")[1])
            finance_data["income"] += amount
            update.message.reply_text(f"Income of {amount} added. Total income: {finance_data['income']}")
        except (ValueError, IndexError):
            update.message.reply_text("Please provide a valid income amount.")
    
    elif command.startswith("expense"):
        try:
            amount = float(command.split(" ")[1])
            finance_data["expenses"] += amount
            update.message.reply_text(f"Expense of {amount} added. Total expenses: {finance_data['expenses']}")
        except (ValueError, IndexError):
            update.message.reply_text("Please provide a valid expense amount.")
    
    elif command == "balance":
        balance = finance_data["income"] - finance_data["expenses"]
        update.message.reply_text(f"Your balance is: {balance}")
    
    else:
        update.message.reply_text("Use /finance income <amount>, /finance expense <amount>, or /finance balance.")

# Study Companion Command Handler (Pomodoro Timer)
def study(update: Update, context: CallbackContext):
    """Start a Pomodoro timer (25 minutes work, 5 minutes break)."""
    if not check_channel_member(update):
        update.message.reply_text(f"Please join the channel first: {CHANNEL_LINK}")
        return

    schedule.every(25).minutes.do(lambda: update.message.reply_text("Work session is over. Take a 5-minute break!"))
    schedule.every(5).minutes.do(lambda: update.message.reply_text("Break time is over. Time to work!"))

    update.message.reply_text("Pomodoro timer started! Work for 25 minutes, then take a 5-minute break.")

    while True:
        schedule.run_pending()
        time.sleep(1)

# Weather Command Handler (OpenWeatherMap API)
def weather(update: Update, context: CallbackContext):
    """Get the current weather using OpenWeatherMap API."""
    if not check_channel_member(update):
        update.message.reply_text(f"Please join the channel first: {CHANNEL_LINK}")
        return

    city = " ".join(context.args)
    if not city:
        update.message.reply_text("Please provide a city name.")
        return

    api_key = os.getenv("WEATHER_API_KEY")
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
    response = requests.get(url)
    weather_data = response.json()

    if weather_data["cod"] == 200:
        main = weather_data["main"]
        weather_desc = weather_data["weather"][0]["description"]
        temperature = main["temp"]
        update.message.reply_text(f"Weather in {city}:\n{weather_desc}\nTemperature: {temperature}°C")
    else:
        update.message.reply_text("City not found!")

# Music Recommendations Command Handler (Last.fm API)
def music(update: Update, context: CallbackContext):
    """Recommend music based on user mood or genre."""
    if not check_channel_member(update):
        update.message.reply_text(f"Please join the channel first: {CHANNEL_LINK}")
        return

    genre = " ".join(context.args)
    if not genre:
        update.message.reply_text("Please provide a genre (e.g., /music pop).")
        return

    api_key = os.getenv("LASTFM_API_KEY")
    url = f"http://ws.audioscrobbler.com/2.0/?method=tag.gettoptracks&tag={genre}&api_key={api_key}&format=json"
    response = requests.get(url)
    music_data = response.json()

    if "error" in music_data:
        update.message.reply_text("Could not find music for that genre.")
    else:
        track = music_data["tracks"]["track"][0]["name"]
        artist = music_data["tracks"]["track"][0]["artist"]["name"]
        update.message.reply_text(f"Top {genre} track: {track} by {artist}")

# Fitness Command Handler
def fitness(update: Update, context: CallbackContext):
    """Track workouts."""
    if not check_channel_member(update):
        update.message.reply_text(f"Please join the channel first: {CHANNEL_LINK}")
        return

    command = " ".join(context.args).lower()

    if command.startswith("log"):
        workout = " ".join(command.split(" ")[1:])
        update.message.reply_text(f"Workout '{workout}' logged!")
    else:
        update.message.reply_text("Use /fitness log <workout> to log a workout.")

# Language Learning Command Handler (Oxford API)
def language(update: Update, context: CallbackContext):
    """Learn a new word daily from an API."""
    if not check_channel_member(update):
        update.message.reply_text(f"Please join the channel first: {CHANNEL_LINK}")
        return

    word_of_the_day = get_word_of_the_day()  # This should interact with an API like Oxford
    update.message.reply_text(f"Word of the Day: {word_of_the_day}")

def get_word_of_the_day():
    """Fetch word of the day from an API."""
    # Example with Oxford API, replace with a real API
    url = "https://api.dictionaryapi.dev/api/v2/entries/en/<word>"
    response = requests.get(url, headers={"app_id": "your_app_id", "app_key": "your_app_key"})
    word_data = response.json()
    return word_data["word"]

# Error handling
def error(update: Update, context: CallbackContext):
    """Log errors caused by updates."""
    logger.warning(f'Update {update} caused error {context.error}')

# Flask app setup for Render deployment
@app.route("/")
def home():
    return "Super Bot is running!"

# Main function to start the bot
def main():
    """Start the bot."""
    updater = Updater(TOKEN, use_context=True)

    # Set up command handlers
    updater.dispatcher.add_handler(CommandHandler("start", start))
    updater.dispatcher.add_handler(CommandHandler("confession", confession))
    updater.dispatcher.add_handler(CommandHandler("quiz", quiz))
    updater.dispatcher.add_handler(CommandHandler("finance", finance))
    updater.dispatcher.add_handler(CommandHandler("study", study))
    updater.dispatcher.add_handler(CommandHandler("weather", weather))
    updater.dispatcher.add_handler(CommandHandler("music", music))
    updater.dispatcher.add_handler(CommandHandler("fitness", fitness))
    updater.dispatcher.add_handler(CommandHandler("language", language))

    # Add message handler for user answers in the quiz
    updater.dispatcher.add_handler(MessageHandler(filters.text & ~filters.command, check_answer))

    # Add error handler
    updater.dispatcher.add_error_handler(error)

    # Start the bot
    updater.start_polling()
    updater.idle()

# Start the Flask app for deployment
def run_flask():
    """Run the Flask app to deploy on Render."""
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))

# Run both the Flask app and the bot in separate threads
if __name__ == "__main__":
    Thread(target=main).start()
    Thread(target=run_flask).start()

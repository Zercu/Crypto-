import telebot
from telebot import types
from datetime import datetime, timedelta
import sqlite3
import uuid
from threading import Timer
import numpy as np
import talib
import requests

# Initialize the bot with your Telegram API token
bot = telebot.TeleBot("6736371777:AAE1I-Blq7ZU5e-KSOeKLvzpD89zybfWueg")

# Admin and Group Chat IDs for security
ADMIN_IDS = [6736371777, 7356218624, 7010512361]  # Replace with your actual Telegram user IDs
GROUP_CHAT_ID = 1002052697876  # Replace with your actual group chat ID where notifications go

# SQLite database connection
conn = sqlite3.connect('crypto_bot.db', check_same_thread=False)
cursor = conn.cursor()

# Create tables for user data, marketplace data, and payment tokens
cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    subscription_active BOOLEAN,
    subscription_expiry TEXT,
    interval INTEGER DEFAULT 60
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS marketplace (
    item_id TEXT PRIMARY KEY,
    name TEXT,
    description TEXT,
    price INTEGER,
    seller_id INTEGER,
    buyer_id INTEGER,
    status TEXT
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS payment_tokens (
    user_id INTEGER PRIMARY KEY,
    token TEXT
)
''')

# Subscription cost and UPI information
SUBSCRIPTION_COST = 350  # in INR
SUBSCRIPTION_DURATION_DAYS = 30
UPI_ID = "9394106494520@paytm"
PAYMENT_INSTRUCTIONS = f"To subscribe, please make a payment of ₹{SUBSCRIPTION_COST} to the following UPI ID and provide a screenshot for verification:\n\nUPI ID: `{UPI_ID}`\n\nOnce your payment is verified by an admin, your subscription will be activated."

# Start command to welcome the user and notify admins
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.chat.id
    name = message.from_user.first_name
    cursor.execute("INSERT OR IGNORE INTO users (user_id, subscription_active) VALUES (?, ?)", (user_id, False))
    conn.commit()
    bot.reply_to(message, f"Welcome {name}! Learn more about the bot below.")
    send_bot_info(user_id)
    bot.send_message(GROUP_CHAT_ID, f"New user started the bot: {name} (Chat ID: {user_id})")

def send_bot_info(user_id):
    info_text = (
        "🤖 *Crypto & Market Prediction Bot*\n\n"
        "This bot provides advanced predictions for various assets such as Bitcoin, Ethereum, Gold, Indian Rupees, American Dollars, and more.\n\n"
        "🔍 *Features:*\n"
        "1. Technical Analysis using Moving Averages, RSI, Bollinger Bands, and more.\n"
        "2. Real-time price monitoring and prediction updates.\n"
        "3. Marketplace for listing and buying items (requires admin approval for sensitive items).\n"
        "4. Subscription management and manual payment verification.\n\n"
        f"{PAYMENT_INSTRUCTIONS}\n\n"
        "Use /subscribe to begin the payment process."
    )
    bot.send_message(user_id, info_text, parse_mode='Markdown')

# Subscription handling
@bot.message_handler(commands=['subscribe'])
def subscribe(message):
    user_id = message.chat.id
    payment_token = str(uuid.uuid4())
    cursor.execute("INSERT OR REPLACE INTO payment_tokens (user_id, token) VALUES (?, ?)", (user_id, payment_token))
    cursor.execute("UPDATE users SET subscription_active = ?, subscription_expiry = ? WHERE user_id = ?", (False, None, user_id))
    conn.commit()
    bot.send_message(user_id, f"Please make a payment of ₹{SUBSCRIPTION_COST} to the UPI ID and send a screenshot for verification. Your payment token is `{payment_token}`.")

@bot.message_handler(commands=['confirm_payment'])
def confirm_payment(message):
    user_id = message.chat.id
    cursor.execute("SELECT subscription_active FROM users WHERE user_id = ?", (user_id,))
    subscription_active = cursor.fetchone()
    if subscription_active and subscription_active[0]:
        bot.reply_to(message, "Your payment has already been verified.")
        return
    
    bot.send_message(user_id, "Please send a screenshot of the payment for verification.")
    bot.register_next_step_handler(message, process_payment_confirmation)

def process_payment_confirmation(message):
    user_id = message.chat.id
    if not message.photo:
        bot.reply_to(message, "Please send a valid screenshot.")
        return

    cursor.execute("SELECT token FROM payment_tokens WHERE user_id = ?", (user_id,))
    payment_token = cursor.fetchone()[0]
    bot.send_message(user_id, "Thank you for the payment details. Please wait for admin approval to activate your subscription.")
    
    for admin_id in ADMIN_IDS:
        keyboard = types.InlineKeyboardMarkup()
        confirm_button = types.InlineKeyboardButton("✅ Confirm Payment", callback_data=f"confirm_{user_id}")
        cancel_button = types.InlineKeyboardButton("❌ Cancel Payment", callback_data=f"cancel_{user_id}")
        keyboard.add(confirm_button, cancel_button)
        bot.send_photo(admin_id, message.photo[-1].file_id, caption=f"User {user_id} has submitted a payment screenshot with token: {payment_token}.", reply_markup=keyboard)

@bot.callback_query_handler(func=lambda call: call.data.startswith("confirm_") or call.data.startswith("cancel_"))
def handle_payment_approval(call):
    user_id = int(call.data.split("_")[1])
    if call.data.startswith("confirm_"):
        cursor.execute("UPDATE users SET subscription_active = ?, subscription_expiry = ? WHERE user_id = ?", (True, (datetime.now() + timedelta(days=SUBSCRIPTION_DURATION_DAYS)).isoformat(), user_id))
        conn.commit()
        bot.send_message(user_id, "Your subscription has been activated! Enjoy premium features.")
        bot.send_message(call.message.chat.id, f"Subscription for user {user_id} has been activated.")
    elif call.data.startswith("cancel_"):
        bot.send_message(user_id, "Your payment could not be verified. Please contact support for assistance.")
        bot.send_message(call.message.chat.id, f"Payment for user {user_id} was canceled.")

# Admin commands
@bot.message_handler(commands=['give_subscription'])
def give_subscription(message):
    if message.chat.id not in ADMIN_IDS:
        bot.reply_to(message, "You are not authorized to give subscriptions.")
        return

    try:
        _, user_id = message.text.split()
        user_id = int(user_id)
        cursor.execute("UPDATE users SET subscription_active = ?, subscription_expiry = ? WHERE user_id = ?", (True, (datetime.now() + timedelta(days=SUBSCRIPTION_DURATION_DAYS)).isoformat(), user_id))
        conn.commit()
        bot.send_message(user_id, "An admin has manually activated your subscription. Enjoy premium features!")
        bot.reply_to(message, f"Subscription for user {user_id} has been manually activated.")
    except ValueError:
        bot.reply_to(message, "Usage: /give_subscription <user_id>")

@bot.message_handler(commands=['set_free_user'])
def set_free_user(message):
    if message.chat.id not in ADMIN_IDS:
        bot.reply_to(message, "You are not authorized to set free users.")
        return

    try:
        _, user_id = message.text.split()
        user_id = int(user_id)
        cursor.execute("UPDATE users SET subscription_active = ?, subscription_expiry = ? WHERE user_id = ?", (True, (datetime.now() + timedelta(days=SUBSCRIPTION_DURATION_DAYS)).isoformat(), user_id))
        conn.commit()
        bot.send_message(user_id, "You have been granted free access to premium features by an admin!")
        bot.reply_to(message, f"User {user_id} has been set as a free user.")
    except ValueError:
        bot.reply_to(message, "Usage: /set_free_user <user_id>")

@bot.message_handler(commands=['announce'])
def announce(message):
    if message.chat.id not in ADMIN_IDS:
        bot.reply_to(message, "You are not authorized to make announcements.")
        return
    
    try:
        announcement = message.text.split(maxsplit=1)[1]
        bot.send_message(GROUP_CHAT_ID, f"📢 *Announcement:* {announcement}", parse_mode='Markdown')
    except IndexError:
        bot.reply_to(message, "Please provide an announcement message after the command.")

# Stop prediction interval
@bot.message_handler(commands=['stop_interval'])
def stop_interval(message):
    user_id = message.chat.id
    if user_id not in user_data:
        bot.reply_to(message, "No interval predictions are running.")
        return

    user_data[user_id]['interval'] = None
    bot.reply_to(message, "Prediction interval stopped.")

# Prediction logic with advanced future prediction (1-10 minutes)
def advanced_prediction_logic(prices):
    prediction_text = ""

    if prices is None or len(prices) < 30:
        return "Insufficient data

    if prices is None or len(prices) < 30:
        return "Insufficient data for advanced prediction."

    short_ma = talib.SMA(prices, timeperiod=10)[-1]
    long_ma = talib.SMA(prices, timeperiod=30)[-1]
    rsi = talib.RSI(prices, timeperiod=14)[-1]
    upperband, middleband, lowerband = talib.BBANDS(prices, timeperiod=20)

    if short_ma > long_ma:
        prediction_text += "🔼 Upward trend detected (Short MA > Long MA).\n"
    else:
        prediction_text += "🔻 Downward trend detected (Short MA < Long MA).\n"

    if rsi > 70:
        prediction_text += "⚠️ RSI indicates overbought conditions (RSI > 70). Consider selling.\n"
    elif rsi < 30:
        prediction_text += "⚠️ RSI indicates oversold conditions (RSI < 30). Consider buying.\n"

    if prices[-1] > upperband[-1]:
        prediction_text += "⚠️ Price is near the upper Bollinger Band. Possible overbought market.\n"
    elif prices[-1] < lowerband[-1]:
        prediction_text += "⚠️ Price is near the lower Bollinger Band. Possible oversold market.\n"

    # Future prediction logic (1-10 minutes)
    future_predictions = []
    for i in range(1, 11):
        future_price = prices[-1] + (np.random.rand() - 0.5) * 0.01 * prices[-1]  # Mock prediction logic
        future_predictions.append(f"{i} min: {future_price:.2f} USD")
    prediction_text += "\n".join(future_predictions) + "\n"

    return prediction_text

def real_time_prediction(user_id):
    prediction_text = ""

    for crypto in ["bitcoin", "ethereum", "litecoin", "ripple", "gold", "usd", "inr", "rub"]:
        prices = fetch_historical_data(crypto)
        if prices is not None:
            advanced_prediction = advanced_prediction_logic(prices)
            prediction_text += f"🔮 {crypto.capitalize()} Advanced Prediction:\n"
            prediction_text += advanced_prediction + "\n"

            current_price = prices[-1]
            avg_price = np.mean(prices)
            if current_price > avg_price * 1.05:
                prediction_text += "🟢 Advice: Consider Selling, price is above average.\n"
            elif current_price < avg_price * 0.95:
                prediction_text += "🔴 Advice: Consider Buying, price is below average.\n"
            else:
                prediction_text += "🟡 Advice: Hold, price is near average.\n"
        else:
            prediction_text += f"Error fetching data for {crypto}.\n"

    bot.send_message(user_id, prediction_text)

    # Set up the next prediction based on the user-defined interval
    interval = user_data.get(user_id, {}).get('interval', 60)  # Default to 60 minutes
    if interval:
        Timer(interval * 60, real_time_prediction, [user_id]).start()

@bot.message_handler(commands=['set_interval'])
def set_interval(message):
    user_id = message.chat.id
    cursor.execute("SELECT subscription_active FROM users WHERE user_id = ?", (user_id,))
    subscription_active = cursor.fetchone()
    if not subscription_active or not subscription_active[0]:
        bot.reply_to(message, "You need an active subscription to set prediction intervals.")
        return

    bot.send_message(user_id, "Please enter the interval in minutes for how often you want to receive predictions:")
    bot.register_next_step_handler(message, save_interval)

def save_interval(message):
    user_id = message.chat.id
    try:
        interval = int(message.text.strip())
        if interval < 1:
            bot.reply_to(user_id, "The interval must be at least 1 minute.")
            return

        cursor.execute("UPDATE users SET interval = ? WHERE user_id = ?", (interval, user_id))
        conn.commit()
        bot.send_message(user_id, f"Prediction interval set to {interval} minutes.")
        real_time_prediction(user_id)
    except ValueError:
        bot.reply_to(user_id, "Please enter a valid number for the interval.")

# Enhanced help command to list all available commands
@bot.message_handler(commands=['help'])
def help_command(message):
    help_text = (
        "👋 *Help and Support*\n\n"
        "Available commands:\n"
        "/start - Start the bot and get information\n"
        "/subscribe - Subscribe to the bot\n"
        "/confirm_payment - Confirm your payment\n"
        "/give_subscription <user_id> - Admin command to give a subscription\n"
        "/set_free_user <user_id> - Admin command to set a free user\n"
        "/announce <message> - Admin command to make an announcement\n"
        "/set_video - Attach a video to a command\n"
        "/marketplace - View marketplace options\n"
        "/list_item - List an item for sale\n"
        "/view_items - View all available items\n"
        "/view_item <item_id> - View details of an item\n"
        "/stats - View bot statistics\n"
        "/set_interval - Set interval for predictions\n"
        "/stop_interval - Stop interval predictions\n"
        "/feedback - Provide feedback\n"
        "/support - Get support link\n"
        "/bot_stats - View bot statistics\n"
        "/remove_user <user_id> - Admin command to remove a user\n"
    )
    bot.send_message(message.chat.id, help_text, parse_mode='Markdown')

# Start the bot polling
if __name__ == "__main__":
    bot.polling(none_stop=True)

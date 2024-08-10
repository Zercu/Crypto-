import telebot
import requests
import numpy as np
import talib  # Technical Analysis library
from threading import Timer
import razorpay
import stripe
import random
from datetime import datetime

# Initialize the bot with the Telegram API token
bot = telebot.TeleBot("6736371777:AAE1I-Blq7ZU5e-KSOeKLvzpD89zybfWueg")

# List of cryptocurrencies to track
CRYPTO_LIST = ["bitcoin", "ethereum", "litecoin", "ripple"]

# Initialize Razorpay and Stripe clients with your credentials
razorpay_client = razorpay.Client(auth=("rzp_test_XXXXXXX", "XXXXXXXXXXXX"))
stripe.api_key = "sk_test_XXXXXXXXXXXX"

# Admin user IDs for security
ADMIN_IDS = [7010512361, 6156332908]  # Replace with your actual Telegram user IDs

# Group Chat ID where reminders will be sent (replace with your group chat ID)
GROUP_CHAT_ID = -1002177338592 # Replace with the actual group chat ID

# User subscription data storage
user_data = {}

# Fetch historical data for technical analysis
def fetch_historical_data(crypto):
    try:
        response = requests.get(f"https://api.coingecko.com/api/v3/coins/{crypto}/market_chart?vs_currency=usd&days=30")
        data = response.json()
        prices = [price[1] for price in data['prices']]  # Extract closing prices
        return np.array(prices)
    except Exception as e:
        return None

# High-level prediction logic using technical indicators
def advanced_prediction_logic(prices):
    prediction_text = ""

    if prices is None or len(prices) < 30:
        return "Insufficient data for advanced prediction."

    # Calculate Moving Averages (Short-term and Long-term)
    short_ma = talib.SMA(prices, timeperiod=10)[-1]
    long_ma = talib.SMA(prices, timeperiod=30)[-1]

    # Calculate RSI (Relative Strength Index)
    rsi = talib.RSI(prices, timeperiod=14)[-1]

    # Calculate Bollinger Bands
    upperband, middleband, lowerband = talib.BBANDS(prices, timeperiod=20)

    # Analyze Moving Averages
    if short_ma > long_ma:
        prediction_text += "🔼 Upward trend detected (Short MA > Long MA).\n"
    else:
        prediction_text += "🔻 Downward trend detected (Short MA < Long MA).\n"

    # Analyze RSI
    if rsi > 70:
        prediction_text += "⚠️ RSI indicates overbought conditions (RSI > 70). Consider selling.\n"
    elif rsi < 30:
        prediction_text += "⚠️ RSI indicates oversold conditions (RSI < 30). Consider buying.\n"

    # Analyze Bollinger Bands
    if prices[-1] > upperband[-1]:
        prediction_text += "⚠️ Price is near the upper Bollinger Band. Possible overbought market.\n"
    elif prices[-1] < lowerband[-1]:
        prediction_text += "⚠️ Price is near the lower Bollinger Band. Possible oversold market.\n"

    return prediction_text

# Prediction function that uses advanced logic
def real_time_prediction(user_id):
    prediction_text = ""
    
    for crypto in CRYPTO_LIST:
        prices = fetch_historical_data(crypto)
        if prices is not None:
            advanced_prediction = advanced_prediction_logic(prices)
            prediction_text += f"🔮 {crypto.capitalize()} Advanced Prediction:\n"
            prediction_text += advanced_prediction + "\n"
        else:
            prediction_text += f"Error fetching data for {crypto}.\n"
    
    bot.send_message(user_id, prediction_text)
    
    # Run this function again after 1 minute to simulate real-time predictions
    interval = user_data.get(user_id, {}).get('interval', 1)  # Default to 1 minute
    Timer(interval * 60, real_time_prediction, [user_id]).start()

@bot.message_handler(commands=['start'])
def start(message):
    name = message.from_user.first_name
    bot.reply_to(message, f"Welcome {name}! Subscribe for real-time crypto trading predictions. Use /subscribe to choose a subscription plan.")

@bot.message_handler(commands=['subscribe'])
def subscribe(message):
    if message.chat.id in ADMIN_IDS:
        bot.reply_to(message, "You're an admin and can use this bot for free!")
        bot.send_message(message.chat.id, "Starting free real-time predictions for you!")
        real_time_prediction(message.chat.id)
    else:
        keyboard = telebot.types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
        button_1 = telebot.types.KeyboardButton(text="250 INR (Razorpay)")
        button_2 = telebot.types.KeyboardButton(text="$10 (Stripe)")
        keyboard.add(button_1, button_2)
        bot.reply_to(message, "Choose a subscription option:", reply_markup=keyboard)

@bot.message_handler(func=lambda message: message.text in ["250 INR (Razorpay)", "$10 (Stripe)"])
def payment_processing(message):
    user_id = message.chat.id
    username = message.from_user.username
    name = message.from_user.first_name
    user_data[user_id] = {'chat_id': user_id, 'username': username, 'name': name}

    if message.text == "250 INR (Razorpay)":
        user_data[user_id]['subscription_price'] = "250 INR"
        order = razorpay_client.order.create(dict(amount=25000, currency="INR", payment_capture=1))
        payment_link = f"https://rzp.io/l/{order['id']}"
        bot.reply_to(message, f"Please pay using this link: {payment_link}")
    elif message.text == "$10 (Stripe)":
        user_data[user_id]['subscription_price'] = "$10"
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'unit_amount': 1000,
                    'product_data': {'name': 'Crypto Trading Predictions'}
                },
                'quantity': 1
            }],
            mode='payment',
            success_url='https://your-success-url.com',
            cancel_url='https://your-cancel-url.com',
        )
        bot.reply_to(message, f"Please pay using this link: {checkout_session.url}")

    bot.reply_to(message, "Once your payment is successful, you'll receive predictions.")
    
    # Wait for payment confirmation before providing predictions (this needs to be implemented)

@bot.message_handler(commands=['set_interval'])
def set_interval(message):
    if message.chat.id in user_data or message.chat.id in ADMIN_IDS:
        keyboard = telebot.types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
        button_1 = telebot.types.KeyboardButton(text="1 Minute")
        button_2 = telebot.types.KeyboardButton(text="2 Minutes")
        button_3 = telebot.types.KeyboardButton(text="3 Minutes")
        button_4 = telebot.types.KeyboardButton(text="4 Minutes")
        button_5 = telebot.types.KeyboardButton(text="5 Minutes")
        keyboard.add(button_1, button_2, button_3, button_4, button_5)
        bot.reply_to(message, "Choose your prediction interval:\n\nShorter intervals increase the chances of timely predictions.", reply_markup=keyboard)

@bot.message_handler(func=lambda message: message.text in ["1 Minute", "2 Minutes", "3 Minutes", "4 Minutes", "5 Minutes"])
def set_interval_response(message):
    interval_map = {
        "1 Minute": 1,
        "2 Minutes": 2,
        "3 Minutes": 3,
        "4 Minutes": 4,
        "5 Minutes": 5
    }
    interval = interval_map[message.text]
    user_data[message.chat.id]['interval'] = interval

    # Calculate interval in minutes and seconds
    minutes = interval
    seconds = interval * 60
    bot.reply_to(message, f"Prediction interval set to {minutes} minute(s) ({seconds} seconds).")
    real_time_prediction(message.chat.id)  # Start sending predictions immediately

@bot.message_handler(commands=['feedback'])
def feedback(message):
    bot.reply_to(message, "Please send your feedback or report any issues:")
    bot.register_next_step_handler(message, save_feedback)

def save_feedback(message):
    feedback_text = message.text
    for admin_id in ADMIN_IDS:
        bot.send_message(admin_id, f"Feedback received:\n{feedback_text}")
    bot.reply_to(message, "Thank you for your feedback! We appreciate it.")

@bot.message_handler(commands=['help'])
def help(message):
    help_text = """
    🤖 **Bot Commands:**
    /start - Start interacting with the bot
    /subscribe - Subscribe to the prediction service
    /set_interval - Set your prediction interval (1-5 minutes)
    /feedback - Send feedback or report an issue
    /help - Display this help message

    **Admin Commands:**
    /admin - Access the admin panel
    """
    bot.reply_to(message, help_text)

@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.from_user.id in ADMIN_IDS:
        keyboard = telebot.types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
        button_1 = telebot.types.KeyboardButton(text="Change Subscription Price")
        button_2 = telebot.types.KeyboardButton(text="Send Announcement")
        keyboard.add(button_1, button_2)
        bot.reply_to(message, "Admin Panel", reply_markup=keyboard)
    else:
        bot.reply_to(message, "You don't have access to the admin panel.")

@bot.message_handler(func=lambda message: message.text == "Change Subscription Price")
def change_price(message):
    if message.from_user.id in ADMIN_IDS:
        bot.reply_to(message, "Enter new subscription price (e.g., 250 INR or $10):")
        bot.register_next_step_handler(message, update_price)
    else:
        bot.reply_to(message, "You don't have access to change the subscription price.")

def update_price(message):
    new_price = message.text
    # Assuming you want to store the new price globally or send a message to all admins
    for admin_id in ADMIN_IDS:
        bot.send_message(admin_id, f"Subscription price updated to {new_price}")
    bot.reply_to(message, f"Subscription price updated to {new_price}")

@bot.message_handler(func=lambda message: message.text == "Send Announcement")
def send_announcement(message):
    if message.from_user.id in ADMIN_IDS:
        bot.reply_to(message, "Enter the announcement text:")
        bot.register_next_step_handler(message, broadcast_announcement)
    else:
        bot.reply_to(message, "You don't have access to send announcements.")

def broadcast_announcement(message):
    announcement_text = message.text
    # Broadcast the announcement to all users (assuming you have a list of user chat IDs)
    for user_id in user_data.keys():
        bot.send_message(user_id, f"📢 Announcement: {announcement_text}")
    bot.reply_to(message, "Announcement sent to all users.")

# Function to handle other non-command messages or errors
@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    bot.reply_to(message, "I'm sorry, I didn't understand that command. Please type /help to see the list of available commands.")

# Start the bot polling
bot.polling()


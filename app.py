# app.py
import telebot
import requests
import numpy as np
import talib
from threading import Timer
import razorpay
from datetime import datetime, timedelta
import uuid
from flask import Flask, request, redirect

# Initialize the Flask app
app = Flask(__name__)

# Initialize the bot with the Telegram API token
bot = telebot.TeleBot("6736371777:AAE1I-Blq7ZU5e-KSOeKLvzpD89zybfWueg")

# List of cryptocurrencies to track
CRYPTO_LIST = ["bitcoin", "ethereum", "litecoin", "ripple"]

# Initialize Razorpay client with your credentials
razorpay_client = razorpay.Client(auth=("YOUR_RAZORPAY_API_KEY", "YOUR_RAZORPAY_API_SECRET"))

# Admin user IDs for security
ADMIN_IDS = [6736371777, 7356218624, 7010512361]  # Replace with your actual Telegram user IDs

# Group Chat ID where reminders will be sent (replace with your group chat ID)
GROUP_CHAT_ID = 1002052697876  # Replace with the actual group chat ID

# User and marketplace data storage
user_data = {}
marketplace_data = {}

# Subscription duration in days (1 month)
SUBSCRIPTION_DURATION_DAYS = 30

# URLs for Razorpay redirection after payment
SUCCESS_URL = "https://your-heroku-app-name.herokuapp.com/payment-success"
CANCEL_URL = "https://your-heroku-app-name.herokuapp.com/payment-cancel"

# Bot logic and handlers
# (Insert all the bot logic, functions, and command handlers here)

# Flask routes for Razorpay webhook and success/cancel URLs
@app.route('/payment-success')
def payment_success():
    payment_id = request.args.get('razorpay_payment_id')
    order_id = request.args.get('razorpay_order_id')
    signature = request.args.get('razorpay_signature')

    # Verify payment using Razorpay API
    try:
        razorpay_client.utility.verify_payment_signature({
            'razorpay_order_id': order_id,
            'razorpay_payment_id': payment_id,
            'razorpay_signature': signature
        })
        
        # Retrieve user ID from the order
        order_details = razorpay_client.order.fetch(order_id)
        user_id = int(order_details['notes']['user_id'])
        
        # Update user subscription or notify them of success
        bot.send_message(user_id, "Payment successful! Your subscription is now active.")
        
        return redirect("https://yourwebsite.com/success-page")  # Redirect to a thank you page
    except razorpay.errors.SignatureVerificationError:
        return "Signature verification failed."

@app.route('/payment-cancel')
def payment_cancel():
    return redirect("https://yourwebsite.com/cancel-page")  # Redirect to a cancellation page

# Start the bot using webhook (recommended for Heroku deployment)
WEBHOOK_URL = f"https://your-heroku-app-name.herokuapp.com/{YOUR_TELEGRAM_API_TOKEN}/webhook"

@app.route(f'/{YOUR_TELEGRAM_API_TOKEN}/webhook', methods=['POST'])
def webhook():
    json_string = request.get_data().decode('UTF-8')
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return '!', 200

# Remove any existing webhook and set the new one
bot.remove_webhook()
bot.set_webhook(url=WEBHOOK_URL)

# Example function to fetch historical data for technical analysis
def fetch_historical_data(crypto):
    try:
        response = requests.get(f"https://api.coingecko.com/api/v3/coins/{crypto}/market_chart?vs_currency=usd&days=30")
        data = response.json()
        prices = [price[1] for price in data['prices']]
        return np.array(prices)
    except Exception as e:
        return None

# Example function for advanced prediction logic
def advanced_prediction_logic(prices):
    prediction_text = ""

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

    return prediction_text

# Example real-time prediction function
def real_time_prediction(user_id):
    prediction_text = ""
    
    for crypto in CRYPTO_LIST:
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

    keyboard = telebot.types.InlineKeyboardMarkup()
    up_tick = telebot.types.InlineKeyboardButton(text="🔼 Up Tick", callback_data=f"up_{user_id}")
    down_tick = telebot.types.InlineKeyboardButton(text="🔻 Down Tick", callback_data=f"down_{user_id}")
    keyboard.add(up_tick, down_tick)
    
    bot.send_message(user_id, prediction_text, reply_markup=keyboard)
    
    interval = user_data.get(user_id, {}).get('interval', 1)
    Timer(interval * 60, real_time_prediction, [user_id]).start()

# Example command handlers (you can add more handlers as needed)
@bot.message_handler(commands=['start'])
def start(message):
    name = message.from_user.first_name
    bot.reply_to(message, f"Welcome {name}! You can use this bot for crypto trading predictions and marketplace. Use /subscribe to choose a prediction plan or /marketplace to list/buy items.")

# Start the Flask server and the bot (Heroku will call this as the entry point)
if __name__ == "__main__":
    app.run(debug=True)


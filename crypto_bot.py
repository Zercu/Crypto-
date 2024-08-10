import telebot
import requests
import razorpay
import stripe
from threading import Timer
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

# Historical data storage
historical_data = {}

# Fetching market sentiment or latest news
def get_market_sentiment():
    try:
        # Placeholder API for market sentiment/news
        response = requests.get("https://api.coingecko.com/api/v3/global")
        data = response.json()
        market_sentiment = data['data']['market_cap_change_percentage_24h_usd']
        sentiment_text = "Market is bullish!" if market_sentiment > 0 else "Market is bearish!"
        return sentiment_text
    except Exception as e:
        return f"Error fetching market sentiment: {str(e)}"

# Generate buy/sell/hold advice
def generate_advice():
    advice_list = ["Sell", "Trade", "Buy", "Hold"]
    return random.choice(advice_list)

# Fetch historical data and provide predictions
def fetch_historical_data(crypto):
    try:
        response = requests.get(f"https://api.coingecko.com/api/v3/coins/{crypto}/market_chart?vs_currency=usd&days=1")
        data = response.json()
        prices = data['prices']
        historical_data[crypto] = prices
    except Exception as e:
        historical_data[crypto] = []
        return f"Error fetching historical data for {crypto}: {str(e)}"

def prediction(user_id):
    prediction_text = ""
    sentiment = get_market_sentiment()
    prediction_text += f"🔮 Market Sentiment: {sentiment}\n\n"
    
    for crypto in CRYPTO_LIST:
        fetch_historical_data(crypto)
        try:
            # Fetching real-time crypto data from a reliable API
            response = requests.get(f"https://api.coingecko.com/api/v3/simple/price?ids={crypto}&vs_currencies=usd")
            data = response.json()
            current_price = data[crypto]["usd"]
            previous_price = current_price * 0.95  # Just an example for a previous price
            percentage_change = ((current_price - previous_price) / previous_price) * 100
            
            if percentage_change > 0:
                prediction_text += f"{crypto.capitalize()}: Price is expected to increase by {percentage_change:.2f}%\n"
            else:
                prediction_text += f"{crypto.capitalize()}: Price is expected to decrease by {abs(percentage_change):.2f}%\n"

            # Add prediction advice
            advice = generate_advice()
            prediction_text += f"🔮 Advice: {advice} now!\n\n"
            
        except Exception as e:
            prediction_text += f"Error fetching data for {crypto}: {str(e)}\n"
    
    bot.send_message(user_id, prediction_text)
    
    # Schedule the next prediction based on the user's chosen interval
    interval = user_data[user_id].get('interval', 1)  # Default to 1 minute if not set
    Timer(interval * 60, prediction, [user_id]).start()

@bot.message_handler(commands=['start'])
def start(message):
    name = message.from_user.first_name
    bot.reply_to(message, f"Welcome {name}! Subscribe for crypto trading predictions. Use /subscribe to choose a subscription plan.")

@bot.message_handler(commands=['subscribe'])
def subscribe(message):
    if message.chat.id in ADMIN_IDS:
        bot.reply_to(message, "You're an admin and can use this bot for free!")
        # Start sending predictions immediately without payment
        bot.send_message(message.chat.id, "Starting free predictions for you!")
        set_interval(message)
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
    prediction(message.chat.id)  # Start sending predictions immediately

@bot.message_handler(commands=['feedback'])
def feedback(message):
    bot.reply_to(message, "Please send your feedback or report any issues:")
    bot.register_next_step_handler(message, save_feedback)

def save_feedback(message):
    feedback_text = message.text
    # Store the feedback or send it to admin
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
    /admin - Access

import telebot
from telebot import types
from datetime import datetime, timedelta
import uuid
from flask import Flask, request
import numpy as np
import talib
import requests
from threading import Timer

# Initialize the bot with your Telegram API token
bot = telebot.TeleBot("6736371777:AAE1I-Blq7ZU5e-KSOeKLvzpD89zybfWueg")

# Admin and Group Chat IDs for security
ADMIN_IDS = [6736371777, 7356218624, 7010512361]  # Replace with your actual Telegram user IDs
GROUP_CHAT_ID = 1002052697876  # Replace with your actual group chat ID where notifications go

# User and marketplace data storage
user_data = {}
marketplace_data = {}

# Subscription duration in days (1 month)
SUBSCRIPTION_DURATION_DAYS = 30

# UPI Payment Information
UPI_ID = "9394106494520@paytm"

# Payment Instructions
PAYMENT_INSTRUCTIONS = (
    "To subscribe, please choose one of the following payment methods:\n\n"
    "1. **UPI Payment**: Make a payment to the following UPI ID and provide the transaction ID or a screenshot.\n"
    f"   UPI ID: `{UPI_ID}`\n\n"
    "Use /subscribe to begin the payment process."
)

# Command to start the bot and send info, also notify admins in group
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.chat.id
    name = message.from_user.first_name
    bot.reply_to(message, f"Welcome {name}! Learn more about the bot below.")
    send_bot_info(user_id)

    # Notify admins of new user
    bot.send_message(GROUP_CHAT_ID, f"New user started the bot: {name} (Chat ID: {user_id})")

def send_bot_info(user_id):
    info_text = (
        "🤖 *Crypto Trading Prediction Bot*\n\n"
        "This bot provides advanced trading predictions for various cryptocurrencies such as Bitcoin, Ethereum, Litecoin, and Ripple.\n\n"
        "🔍 *Features:*\n"
        "1. Technical Analysis using Moving Averages, RSI, Bollinger Bands, and more.\n"
        "2. Real-time price monitoring and prediction updates.\n"
        "3. Marketplace for listing and buying items.\n"
        "4. Subscription management and manual payment verification.\n\n"
        f"{PAYMENT_INSTRUCTIONS}\n\n"
        "Once your payment is verified by an admin, your subscription will be activated. Use /subscribe to begin."
    )
    bot.send_message(user_id, info_text, parse_mode='Markdown')

@bot.message_handler(commands=['subscribe'])
def subscribe(message):
    user_id = message.chat.id
    user_data[user_id] = {
        'status': 'awaiting_payment',
        'payment_verified': False,
        'subscription_active': False
    }

    keyboard = types.InlineKeyboardMarkup()
    upi_button = types.InlineKeyboardButton("Pay via UPI", callback_data="pay_upi")
    keyboard.add(upi_button)
    
    bot.send_message(user_id, "Choose your preferred payment method:", reply_markup=keyboard)

@bot.callback_query_handler(func=lambda call: call.data == "pay_upi")
def handle_payment_choice(call):
    user_id = call.message.chat.id
    bot.send_message(user_id, f"Please make a payment to the following UPI ID: `{UPI_ID}`.\nAfter payment, use /confirm_payment to submit the transaction details.", parse_mode='Markdown')

@bot.message_handler(commands=['confirm_payment'])
def confirm_payment(message):
    user_id = message.chat.id
    if user_data.get(user_id, {}).get('payment_verified', False):
        bot.reply_to(message, "Your payment has already been verified.")
        return
    
    bot.send_message(user_id, "Please send your UPI transaction ID or a screenshot of the payment for verification.")
    bot.register_next_step_handler(message, process_payment_confirmation)

def process_payment_confirmation(message):
    user_id = message.chat.id
    user_data[user_id]['payment_details'] = message.text
    bot.send_message(user_id, "Thank you for the payment details. Please wait for admin approval to activate your subscription.")

    # Send details to admins for verification
    for admin_id in ADMIN_IDS:
        keyboard = types.InlineKeyboardMarkup()
        confirm_button = types.InlineKeyboardButton("✅ Confirm Payment", callback_data=f"confirm_{user_id}")
        cancel_button = types.InlineKeyboardButton("❌ Cancel Payment", callback_data=f"cancel_{user_id}")
        keyboard.add(confirm_button, cancel_button)

        bot.send_message(admin_id, f"User {user_id} has submitted payment details: {message.text}", reply_markup=keyboard)

@bot.callback_query_handler(func=lambda call: call.data.startswith("confirm_") or call.data.startswith("cancel_"))
def handle_payment_approval(call):
    admin_id = call.message.chat.id
    user_id = int(call.data.split("_")[1])

    if call.data.startswith("confirm_"):
        user_data[user_id]['subscription_active'] = True
        user_data[user_id]['subscription_expiry'] = datetime.now() + timedelta(days=SUBSCRIPTION_DURATION_DAYS)
        bot.send_message(user_id, "Your subscription has been activated! Enjoy premium features.")
        bot.send_message(admin_id, f"Subscription for user {user_id} has been activated.")
    elif call.data.startswith("cancel_"):
        bot.send_message(user_id, "Your payment could not be verified. Please contact support for assistance.")
        bot.send_message(admin_id, f"Payment for user {user_id} was canceled.")

# Admin command to give subscription manually through chat ID
@bot.message_handler(commands=['give_subscription'])
def give_subscription(message):
    if message.chat.id not in ADMIN_IDS:
        bot.reply_to(message, "You are not authorized to give subscriptions.")
        return

    try:
        _, user_id = message.text.split()
        user_id = int(user_id)
        user_data[user_id]['subscription_active'] = True
        user_data[user_id]['subscription_expiry'] = datetime.now() + timedelta(days=SUBSCRIPTION_DURATION_DAYS)
        bot.send_message(user_id, "An admin has manually activated your subscription. Enjoy premium features!")
        bot.reply_to(message, f"Subscription for user {user_id} has been manually activated.")
    except ValueError:
        bot.reply_to(message, "Usage: /give_subscription <user_id>")

# Example command handlers (you can add more handlers as needed)
@bot.message_handler(commands=['predictions'])
def predictions(message):
    user_id = message.chat.id
    if not user_data.get(user_id, {}).get('subscription_active', False):
        bot.reply_to(message, "You need an active subscription to view predictions. Please subscribe using /subscribe.")
        return
    
    # Example of enhanced prediction logic
    prediction_text = "Sample prediction based on current data (logic to be expanded)."
    bot.send_message(user_id, prediction_text)

# Example of an enhanced marketplace (add more logic as needed)
@bot.message_handler(commands=['marketplace'])
def marketplace(message):
    user_id = message.chat.id
    bot.reply_to(message, "Welcome to the Marketplace! You can list items or browse and buy items. Use /list_item to add your item or /view_items to see what's available.")

@bot.message_handler(commands=['list_item'])
def list_item(message):
    bot.send_message(message.chat.id, "Please send the item details in the format: Name, Description, Price.")
    bot.register_next_step_handler(message, save_item)

def save_item(message):
    user_id = message.chat.id
    try:
        item_name, item_description, item_price = message.text.split(',')
        item_id = str(uuid.uuid4())
        marketplace_data[item_id] = {
            'name': item_name.strip(),
            'description': item_description.strip(),
            'price': item_price.strip(),
            'seller_id': user_id,
            'buyer_id': None,
            'status': 'available'
        }
        bot.send_message(user_id, f"Item listed successfully! ID: {item_id}")
    except ValueError:
        bot.send_message(user_id, "Invalid format. Please try again using the format: Name, Description, Price.")

@bot.message_handler(commands=['view_items'])
def view_items(message):
    if not marketplace_data:
        bot.reply_to(message, "No items listed yet.")
        return
    
    items_text = "📦 *Marketplace Items:*\n\n"
    for item_id, details in marketplace_data.items():
        
        items_text += f"ID: {item_id}\nName: {details['name']}\nDescription: {details['description']}\nPrice: {details['price']} INR\nStatus: {details['status']}\n\n"

    bot.send_message(message.chat.id, items_text, parse_mode='Markdown')

@bot.message_handler(commands=['buy_item'])
def buy_item(message):
    bot.send_message(message.chat.id, "Please send the ID of the item you wish to buy.")
    bot.register_next_step_handler(message, process_purchase)

def process_purchase(message):
    user_id = message.chat.id
    item_id = message.text.strip()

    if item_id not in marketplace_data:
        bot.reply_to(message, "Invalid item ID. Please try again.")
        return

    item = marketplace_data[item_id]
    if item['status'] != 'available':
        bot.reply_to(message, "This item is no longer available.")
        return

    item['buyer_id'] = user_id
    item['status'] = 'pending_payment'
    bot.send_message(user_id, f"You have selected to buy: {item['name']} for {item['price']} INR. Please make a payment to the following UPI ID: `{UPI_ID}` and use /confirm_purchase {item_id} to confirm your payment.", parse_mode='Markdown')

    # Notify the seller
    bot.send_message(item['seller_id'], f"Your item '{item['name']}' has been selected for purchase by user {user_id}. Please await payment confirmation.")

@bot.message_handler(commands=['confirm_purchase'])
def confirm_purchase(message):
    user_id = message.chat.id
    try:
        _, item_id = message.text.split()
        item_id = item_id.strip()
    except ValueError:
        bot.reply_to(message, "Invalid format. Use /confirm_purchase <item_id>")
        return

    if item_id not in marketplace_data:
        bot.reply_to(message, "Invalid item ID. Please try again.")
        return

    item = marketplace_data[item_id]
    if item['buyer_id'] != user_id:
        bot.reply_to(message, "You are not the buyer of this item.")
        return

    bot.send_message(user_id, "Please send your UPI transaction ID or a screenshot of the payment for verification.")
    bot.register_next_step_handler(message, lambda msg: finalize_purchase(msg, item_id))

def finalize_purchase(message, item_id):
    buyer_id = message.chat.id
    item = marketplace_data[item_id]

    item['payment_details'] = message.text
    bot.send_message(buyer_id, "Thank you for the payment details. Please wait for admin approval to complete the purchase.")

    # Notify admins for payment verification
    for admin_id in ADMIN_IDS:
        keyboard = types.InlineKeyboardMarkup()
        confirm_button = types.InlineKeyboardButton("✅ Confirm Payment", callback_data=f"confirm_purchase_{item_id}")
        cancel_button = types.InlineKeyboardButton("❌ Cancel Payment", callback_data=f"cancel_purchase_{item_id}")
        keyboard.add(confirm_button, cancel_button)

        bot.send_message(admin_id, f"User {buyer_id} has submitted payment details for item {item_id}: {item['payment_details']}", reply_markup=keyboard)

@bot.callback_query_handler(func=lambda call: call.data.startswith("confirm_purchase_") or call.data.startswith("cancel_purchase_"))
def handle_purchase_approval(call):
    admin_id = call.message.chat.id
    item_id = call.data.split("_")[2]

    if call.data.startswith("confirm_purchase_"):
        item = marketplace_data[item_id]
        item['status'] = 'sold'
        bot.send_message(item['buyer_id'], f"Your payment has been confirmed! You have successfully purchased '{item['name']}'.")
        bot.send_message(item['seller_id'], f"Your item '{item['name']}' has been sold. Please arrange delivery with the buyer.")
        bot.send_message(admin_id, f"Purchase of item {item_id} has been confirmed.")

    elif call.data.startswith("cancel_purchase_"):
        item = marketplace_data[item_id]
        item['status'] = 'available'
        bot.send_message(item['buyer_id'], "Your payment could not be verified. The purchase has been canceled. Please try again.")
        bot.send_message(item['seller_id'], f"The sale of your item '{item['name']}' has been canceled.")
        bot.send_message(admin_id, f"Purchase of item {item_id} has been canceled.")

# Admin command to give subscription manually through chat ID
@bot.message_handler(commands=['give_subscription'])
def give_subscription(message):
    if message.chat.id not in ADMIN_IDS:
        bot.reply_to(message, "You are not authorized to give subscriptions.")
        return

    try:
        _, user_id = message.text.split()
        user_id = int(user_id)
        user_data[user_id]['subscription_active'] = True
        user_data[user_id]['subscription_expiry'] = datetime.now() + timedelta(days=SUBSCRIPTION_DURATION_DAYS)
        bot.send_message(user_id, "An admin has manually activated your subscription. Enjoy premium features!")
        bot.reply_to(message, f"Subscription for user {user_id} has been manually activated.")
    except ValueError:
        bot.reply_to(message, "Usage: /give_subscription <user_id>")

# Command to handle user feedback
@bot.message_handler(commands=['feedback'])
def feedback(message):
    user_id = message.chat.id
    bot.send_message(user_id, "Please send your feedback or report any issues.")
    bot.register_next_step_handler(message, save_feedback)

def save_feedback(message):
    feedback_text = message.text
    user_id = message.chat.id

    # Forward the feedback to all admins
    for admin_id in ADMIN_IDS:
        bot.send_message(admin_id, f"Feedback from user {user_id}: {feedback_text}")

    bot.reply_to(message, "Thank you for your feedback!")

# Command to get help and support
@bot.message_handler(commands=['help'])
def help(message):
    support_group_link = "https://t.me/your_support_group"  # Replace with your support group link
    help_text = (
        "👋 *Help and Support*\n\n"
        "For any issues, please contact us or join our support group.\n\n"
        f"Support Group: [Join Here]({support_group_link})\n\n"
        "Use /feedback to report any issues or provide feedback."
    )
    bot.send_message(message.chat.id, help_text, parse_mode='Markdown')

# Improved prediction logic (this can be expanded with more complex calculations)
def fetch_historical_data(crypto):
    try:
        response = requests.get(f"https://api.coingecko.com/api/v3/coins/{crypto}/market_chart?vs_currency=usd&days=30")
        data = response.json()
        prices = [price[1] for price in data['prices']]
        return np.array(prices)
    except Exception as e:
        return None

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

def real_time_prediction(user_id):
    prediction_text = ""
    
    for crypto in ["bitcoin", "ethereum", "litecoin", "ripple"]:
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

# Start the bot polling
if __name__ == "__main__":
    bot.polling(none_stop=True)

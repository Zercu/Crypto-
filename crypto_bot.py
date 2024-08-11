import telebot
import requests
import numpy as np
import talib  # Technical Analysis library
from threading import Timer
import razorpay
import random
from datetime import datetime, timedelta
import uuid  # For generating unique tokens

# Initialize the bot with the Telegram API token
bot = telebot.TeleBot("YOUR_TELEGRAM_API_TOKEN")

# List of cryptocurrencies to track
CRYPTO_LIST = ["bitcoin", "ethereum", "litecoin", "ripple"]

# Initialize Razorpay client with your credentials
razorpay_client = razorpay.Client(auth=("rzp_test_XXXXXXX", "XXXXXXXXXXXX"))

# Admin user IDs for security
ADMIN_IDS = [7010512361, 6156332908]  # Replace with your actual Telegram user IDs

# Group Chat ID where reminders will be sent (replace with your group chat ID)
GROUP_CHAT_ID = -1002177338592  # Replace with the actual group chat ID

# User and marketplace data storage
user_data = {}
marketplace_data = {}

# Subscription duration in days (1 month)
SUBSCRIPTION_DURATION_DAYS = 30

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
            
            # Simple heuristic: give advice based on current price vs historical average
            current_price = prices[-1]
            avg_price = np.mean(prices)
            if current_price > avg_price * 1.05:  # If current price is 5% above average
                prediction_text += "🟢 Advice: Consider Selling, price is above average.\n"
            elif current_price < avg_price * 0.95:  # If current price is 5% below average
                prediction_text += "🔴 Advice: Consider Buying, price is below average.\n"
            else:
                prediction_text += "🟡 Advice: Hold, price is near average.\n"
        else:
            prediction_text += f"Error fetching data for {crypto}.\n"

    # Adding Up Tick and Down Tick functionality
    keyboard = telebot.types.InlineKeyboardMarkup()
    up_tick = telebot.types.InlineKeyboardButton(text="🔼 Up Tick", callback_data=f"up_{user_id}")
    down_tick = telebot.types.InlineKeyboardButton(text="🔻 Down Tick", callback_data=f"down_{user_id}")
    keyboard.add(up_tick, down_tick)
    
    bot.send_message(user_id, prediction_text, reply_markup=keyboard)
    
    # Run this function again after the interval set by the user
    interval = user_data.get(user_id, {}).get('interval', 1)  # Default to 1 minute
    Timer(interval * 60, real_time_prediction, [user_id]).start()

@bot.callback_query_handler(func=lambda call: call.data.startswith('up_') or call.data.startswith('down_'))
def handle_tick(call):
    user_id = int(call.data.split('_')[1])
    if call.data.startswith('up_'):
        bot.send_message(user_id, "🔼 You clicked Up Tick! Let's see if your prediction is correct.")
    elif call.data.startswith('down_'):
        bot.send_message(user_id, "🔻 You clicked Down Tick! Let's see if your prediction is correct.")

@bot.message_handler(commands=['start'])
def start(message):
    name = message.from_user.first_name
    bot.reply_to(message, f"Welcome {name}! You can use this bot for crypto trading predictions and marketplace. Use /subscribe to choose a prediction plan or /marketplace to list/buy items.")

@bot.message_handler(commands=['subscribe'])
def subscribe(message):
    if message.chat.id in ADMIN_IDS:
        bot.reply_to(message, "You're an admin and can use this bot for free!")
        bot.send_message(message.chat.id, "Starting free real-time predictions for you!")
        real_time_prediction(message.chat.id)
    else:
        keyboard = telebot.types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
        button_1 = telebot.types.KeyboardButton(text="250 INR (Razorpay)")
        button_2 = telebot.types.KeyboardButton(text="(COMING SOON) PayPal")
        keyboard.add(button_1, button_2)
        bot.reply_to(message, "Choose a subscription option:", reply_markup=keyboard)

@bot.message_handler(func=lambda message: message.text in ["250 INR (Razorpay)", "(COMING SOON) PayPal"])
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
    elif message.text == "(COMING SOON) PayPal":
        bot.reply_to(message, "PayPal integration is coming soon. Stay tuned!")

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
    (bot.register_next_step_handler(message, save_feedback)

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
    /marketplace - Access the marketplace to list or buy items
    /help - Display this help message

    **Admin Commands:**
    /admin - Access the admin panel
    /approve_delete - Approve a seller's delete request for a product
    /deny_delete - Deny a seller's delete request for a product
    """
    bot.reply_to(message, help_text)

@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.from_user.id in ADMIN_IDS:
        keyboard = telebot.types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
        button_1 = telebot.types.KeyboardButton(text="Change Subscription Price")
        button_2 = telebot.types.KeyboardButton(text="Send Announcement")
        button_3 = telebot.types.KeyboardButton(text="View Subscriptions")
        button_4 = telebot.types.KeyboardButton(text="List Item (Admin)")
        keyboard.add(button_1, button_2, button_3, button_4)
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

@bot.message_handler(func=lambda message: message.text == "View Subscriptions")
def view_subscriptions(message):
    if message.from_user.id in ADMIN_IDS:
        subscription_info = "📊 **Current Subscriptions**:\n"
        for user_id, data in user_data.items():
            name = data.get('name', 'Unknown')
            expiry = data.get('subscription_expiry', 'Not Subscribed')
            subscription_info += f"• {name}: Subscription ends on {expiry}\n"
        bot.reply_to(message, subscription_info)
    else:
        bot.reply_to(message, "You don't have access to view subscriptions.")

# Function to list an item, now also available to admins
@bot.message_handler(func=lambda message: message.text in ["List Item", "List Item (Admin)"])
def list_item(message):
    bot.reply_to(message, "Please send the item details in the following format:\n\nItem Name, Description, Price in INR, Your Paytm/UPI ID")
    bot.register_next_step_handler(message, save_item)

def save_item(message):
    try:
        item_details = message.text.split(',')
        item_name = item_details[0].strip()
        item_description = item_details[1].strip()
        item_price = int(item_details[2].strip())
        upi_id = item_details[3].strip()
        
        # Generate a unique item token
        item_token = str(uuid.uuid4())
        marketplace_data[item_token] = {
            'name': item_name, 
            'description': item_description, 
            'price': item_price, 
            'upi_id': upi_id, 
            'seller_id': message.chat.id,
            'token': item_token
        }

        bot.reply_to(message, f"Item listed successfully!\nYour item token is: `{item_token}`.\n\nUse this token to manage your item.")
    except Exception as e:
        bot.reply_to(message, "Error in listing item. Please ensure you follow the correct format.")

# Function to handle delete requests by sellers
@bot.message_handler(commands=['request_delete'])
def request_delete(message):
    bot.reply_to(message, "Please send the item token you want to delete:")
    bot.register_next_step_handler(message, process_delete_request)

def process_delete_request(message):
    item_token = message.text.strip()
    if item_token in marketplace_data:
        item = marketplace_data[item_token]
        if message.chat.id == item['seller_id']:
            bot.reply_to(message, "Delete request received. Admins will review your request.")
            for admin_id in ADMIN_IDS:
                bot.send_message(admin_id, f"Delete request for item: {item['name']}. Token: {item_token}. Approve or deny using /approve_delete or /deny_delete followed by the token.")
        else:
            bot.reply_to(message, "You do not have permission to delete this item.")
    else:
        bot.reply_to(message, "Invalid item token. Please try again.")

# Admin approves or denies the delete request
@bot.message_handler(commands=['approve_delete'])
def approve_delete(message):
    args = message.text.split(' ')
    if len(args) != 2:
        bot.reply_to(message, "Usage: /approve_delete <item_token>")
        return

    item_token = args[1].strip()
    item = marketplace_data.get(item_token)
    if item is not None:
        item = marketplace_data.pop(item_token, None)
        bot.reply_to(message, f"Item '{item['name']}' has been deleted.")
    else:
        bot.reply_to(message, "Invalid item token.")

@bot.message_handler(commands=['deny_delete'])
def deny_delete(message):
    args = message.text.split(' ')
    if len(args) != 2:
        bot.reply_to(message, "Usage: /deny_delete <item_token>")
        return

    item_token = args[1].strip()
    item = marketplace_data.get(item_token)
    if item is not None:
        bot.reply_to(message, f"Delete request denied for item '{marketplace_data[item_token]['name']}'.")
    else:
        bot.reply_to(message, "Invalid item token.")

@bot.message_handler(commands=['marketplace'])
def marketplace(message):
    keyboard = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    button_1 = telebot.types.KeyboardButton(text="List Item")
    button_2 = telebot.types.KeyboardButton(text="View Items")
    keyboard.add(button_1, button_2)
    bot.reply_to(message, "Welcome to the Marketplace! Choose an option:", reply_markup=keyboard)

@bot.message_handler(func=lambda message: message.text == "View Items")
def view_items(message):
    if not marketplace_data:
        bot.reply_to(message, "No items currently listed in the marketplace.")
        return
    
    items_text = "📦 **Marketplace Items**:\n\n"
    for item_token, details in marketplace_data.items():
        items_text += f"Item Token: `{item_token}`\nName: {details['name']}\nDescription: {details['description']}\nPrice: {details['price']} INR\n\n"
    
    bot.reply_to(message, items_text)
    bot.reply_to(message, "To purchase an item, type the item token and confirm your payment using your UPI.")

@bot.message_handler(func=lambda message: message.text in marketplace_data.keys())
def purchase_item(message):
    item_token = message.text.strip()
    if item_token in marketplace_data:
        item = marketplace_data[item_token]
        bot.reply_to(message, f"Please pay {item['price']} INR using UPI to {item['upi_id']}. After payment, reply with your UPI transaction ID for verification.")
        bot.register_next_step_handler(message, verify_purchase, item_token)
    else:
        bot.reply_to(message, "Invalid item token. Please check and try again.")

def verify_purchase(message, item_token):
    upi_transaction_id = message.text.strip()
    buyer_id = message.chat.id

    if len(upi_transaction_id) > 5:  # Basic validity check
        item = marketplace_data.get(item_token)
        if item is not None:
            commission = int(item['price'] * 0.25)
            seller_amount = item['price'] - commission
            
            # Notify the buyer
            bot.reply_to(buyer_id, f"Payment verified! The seller will be notified to dispatch the item: {item['name']}.")
            
            # Notify the seller
                        bot.send_message(item['seller_id'], f"Your item '{item['name']}' has been sold! You will receive {seller_amount} INR after a 25% commission deduction.\n\nPlease dispatch the item to the buyer and confirm the sale using your token.")

            # Notify the admins
            for admin_id in ADMIN_IDS:
                bot.send_message(admin_id, f"⚠️ **Purchase Alert** ⚠️\n\n"
                                           f"Item: {item['name']}\n"
                                           f"Price: {item['price']} INR\n"
                                           f"Seller: {item['seller_id']}\n"
                                           f"Buyer: {buyer_id}\n"
                                           f"Transaction ID: {upi_transaction_id}\n\n"
                                           "Please ensure the transaction is completed and handle any disputes if they arise.")
            
            # Store transaction data and remove the item from the marketplace
            marketplace_data.pop(item_token, None)
            
            # In a real implementation, you should store this data in a database for record-keeping and verification.
        
        else:
            bot.reply_to(message, "Invalid item token. Please check and try again.")
    else:
        bot.reply_to(message, "Invalid UPI transaction ID. Please check and try again.")

@bot.message_handler(func=lambda message: message.text.startswith('/confirm'))
def confirm_sale(message):
    try:
        args = message.text.split(' ')
        if len(args) != 2:
            bot.reply_to(message, "Usage: /confirm <item_token>")
            return

        item_token = args[1].strip()
        item = marketplace_data.get(item_token)
        if item is not None and message.chat.id == item['seller_id']:
            bot.reply_to(message, f"Sale confirmed for item: {item['name']}. The buyer has been notified.")
            # Here, you would typically process the payment and notify the buyer that the item is on the way.
            # This would involve updating your records and possibly handling delivery.
        else:
            bot.reply_to(message, "You are not authorized to confirm this sale or the item token is invalid.")
    except Exception as e:
        bot.reply_to(message, "Error confirming sale. Please try again.")

# Function to handle other non-command messages or errors
@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    bot.reply_to(message, "I'm sorry, I didn't understand that command. Please type /help to see the list of available commands.")

# Start the bot polling
bot.polling()


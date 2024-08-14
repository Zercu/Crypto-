import telebot
from telebot import types
from datetime import datetime, timedelta
import uuid
import logging
import requests
from requests.exceptions import RequestException
import numpy as np
import talib
import psycopg2
from apscheduler.schedulers.background import BackgroundScheduler

# Initialize logging
logging.basicConfig(level=logging.INFO)

# Initialize the bot with your Telegram API token
bot = telebot.TeleBot("6736371777:AAE1I-Blq7ZU5e-KSOeKLvzpD89zybfWueg")

# Admin and Group Chat IDs for security
ADMIN_IDS = [6736371777, 7356218624, 7010512361]  # Replace with your actual Telegram user IDs
GROUP_CHAT_ID = 1002052697876  # Replace with your actual group chat ID where notifications go

# Subscription cost
SUBSCRIPTION_COST = 350  # in INR

# Subscription duration in days (1 month)
SUBSCRIPTION_DURATION_DAYS = 30

# UPI Payment Information
UPI_ID = "9394106494520@paytm"

# Payment Instructions
PAYMENT_INSTRUCTIONS = (
    f"To subscribe, please make a payment of ₹{SUBSCRIPTION_COST} to the following UPI ID and provide a screenshot for verification:\n\n"
    f"UPI ID: `{UPI_ID}`\n\n"
    "Once your payment is verified by an admin, your subscription will be activated."
)

# PostgreSQL connection setup
conn = psycopg2.connect(
    dbname='your_db_name', user='your_db_user', password='your_db_password', host='localhost', port='5432'
)
cursor = conn.cursor()

# Create necessary tables
cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id BIGINT PRIMARY KEY,
        status TEXT,
        payment_verified BOOLEAN DEFAULT FALSE,
        subscription_active BOOLEAN DEFAULT FALSE,
        subscription_expiry TIMESTAMP,
        payment_token TEXT,
        interval INTEGER DEFAULT 60
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS marketplace (
        item_id UUID PRIMARY KEY,
        name TEXT,
        description TEXT,
        price TEXT,
        seller_id BIGINT REFERENCES users(user_id),
        buyer_id BIGINT,
        status TEXT
    )
''')

conn.commit()

# Scheduler for real-time predictions
scheduler = BackgroundScheduler()
scheduler.start()

def fetch_historical_data(crypto):
    try:
        response = requests.get(f"https://api.coingecko.com/api/v3/coins/{crypto}/market_chart?vs_currency=usd&days=30")
        response.raise_for_status()  # Raises an error for bad responses
        data = response.json()
        prices = [price[1] for price in data['prices']]
        return np.array(prices)
    except RequestException as e:
        logging.error(f"Error fetching data for {crypto}: {e}")
        return None

def advanced_prediction_logic(prices):
    if prices is None or len(prices) < 30:
        return "Insufficient data for advanced prediction."

    short_ma = talib.SMA(prices, timeperiod=10)[-1]
    long_ma = talib.SMA(prices, timeperiod=30)[-1]
    rsi = talib.RSI(prices, timeperiod=14)[-1]
    upperband, middleband, lowerband = talib.BBANDS(prices, timeperiod=20)

    prediction_text = ""
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
    cursor.execute("SELECT interval FROM users WHERE user_id = %s", (user_id,))
    user = cursor.fetchone()
    interval = user[0] if user else 60  # Default to 60 minutes

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
    scheduler.add_job(real_time_prediction, 'interval', minutes=interval, args=[user_id])

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.chat.id
    name = message.from_user.first_name

    # Check if the user is already in the database
    cursor.execute("SELECT user_id FROM users WHERE user_id = %s", (user_id,))
    if not cursor.fetchone():
        cursor.execute("INSERT INTO users (user_id, status) VALUES (%s, %s)", (user_id, 'new_user'))
        conn.commit()

    bot.reply_to(message, f"Welcome {name}! Learn more about the bot below.")
    send_bot_info(user_id)

    # Notify admins of new user
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

@bot.message_handler(commands=['subscribe'])
def subscribe(message):
    user_id = message.chat.id
    payment_token = str(uuid.uuid4())

    cursor.execute("""
        UPDATE users
        SET status = 'awaiting_payment',
            payment_verified = FALSE,
            subscription_active = FALSE,
            payment_token = %s
        WHERE user_id = %s
    """, (payment_token, user_id))
    conn.commit()

    bot.send_message(user_id, f"Please make a payment of ₹{SUBSCRIPTION_COST} to the UPI ID and send a screenshot for verification. Your payment token is `{payment_token}`.")

@bot.message_handler(commands=['confirm_payment'])
def confirm_payment(message):
    user_id = message.chat.id
    cursor.execute("SELECT payment_verified FROM users WHERE user_id = %s", (user_id,))
    payment_verified = cursor.fetchone()[0]

    if payment_verified:
        bot.reply_to(message, "Your payment has already been verified.")
        return
    
    bot.send_message(user_id, "Please send a screenshot of the payment for verification.")
    bot.register_next_step_handler(message, process_payment_confirmation)

def process_payment_confirmation(message):
    user_id = message.chat.id
    if not message.photo:
        bot.reply_to(message, "Please send a valid screenshot.")
        return

    payment_screenshot = message.photo[-1].file_id

    cursor.execute("UPDATE users SET payment_screenshot = %s WHERE user_id = %s", (payment_screenshot, user_id))
    conn.commit()

    bot.send_message(user_id, "Thank you for the payment details. Please wait for admin approval to activate your subscription.")

    # Send screenshot and details to admins for verification
    for admin_id in ADMIN_IDS:
        keyboard = types.InlineKeyboardMarkup()
        confirm_button = types.InlineKeyboardButton("✅ Confirm Payment", callback_data=f"confirm_{user_id}")
        cancel_button = types.InlineKeyboardButton("❌ Cancel Payment", callback_data=f"cancel_{user_id}")
        keyboard.add(confirm_button, cancel_button)

                bot.send_photo(admin_id, payment_screenshot, caption=f"User {user_id} has submitted a payment screenshot with token: {payment_token}.", reply_markup=keyboard)

@bot.callback_query_handler(func=lambda call: call.data.startswith("confirm_") or call.data.startswith("cancel_"))
def handle_payment_approval(call):
    admin_id = call.message.chat.id
    user_id = int(call.data.split("_")[1])

    if call.data.startswith("confirm_"):
        cursor.execute("""
            UPDATE users
            SET subscription_active = TRUE,
                subscription_expiry = %s,
                payment_verified = TRUE
            WHERE user_id = %s
        """, (datetime.now() + timedelta(days=SUBSCRIPTION_DURATION_DAYS), user_id))
        conn.commit()

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

        cursor.execute("""
            UPDATE users
            SET subscription_active = TRUE,
                subscription_expiry = %s,
                payment_verified = TRUE
            WHERE user_id = %s
        """, (datetime.now() + timedelta(days=SUBSCRIPTION_DURATION_DAYS), user_id))
        conn.commit()

        bot.send_message(user_id, "An admin has manually activated your subscription. Enjoy premium features!")
        bot.reply_to(message, f"Subscription for user {user_id} has been manually activated.")
    except ValueError:
        bot.reply_to(message, "Usage: /give_subscription <user_id>")

# Admin command to set free users (bypasses payment requirement)
@bot.message_handler(commands=['set_free_user'])
def set_free_user(message):
    if message.chat.id not in ADMIN_IDS:
        bot.reply_to(message, "You are not authorized to set free users.")
        return

    try:
        _, user_id = message.text.split()
        user_id = int(user_id)

        cursor.execute("""
            UPDATE users
            SET status = 'free_user',
                subscription_active = TRUE,
                subscription_expiry = %s,
                payment_verified = TRUE
            WHERE user_id = %s
        """, (datetime.now() + timedelta(days=SUBSCRIPTION_DURATION_DAYS), user_id))
        conn.commit()

        bot.send_message(user_id, "You have been granted free access to premium features by an admin!")
        bot.reply_to(message, f"User {user_id} has been set as a free user.")
    except ValueError:
        bot.reply_to(message, "Usage: /set_free_user <user_id>")

# Admin command to announce messages
@bot.message_handler(commands=['announce'])
def announce(message):
    if message.chat.id not in ADMIN_IDS:
        bot.reply_to(message, "You are not authorized to make announcements.")
        return

    announcement = message.text.split(maxsplit=1)[1]  # Get the announcement text
    bot.send_message(GROUP_CHAT_ID, f"📢 *Announcement:* {announcement}", parse_mode='Markdown')

# Admin command to set instructional video
@bot.message_handler(commands=['set_video'])
def set_video(message):
    if message.chat.id not in ADMIN_IDS:
        bot.reply_to(message, "You are not authorized to set videos.")
        return
    
    bot.send_message(message.chat.id, "Please send the command you want to attach the video to, followed by the video file.")
    bot.register_next_step_handler(message, save_video)

def save_video(message):
    try:
        command = message.text.split()[0]
        if command not in ['/start', '/subscribe', '/confirm_payment', '/marketplace']:
            bot.reply_to(message, "Invalid command. Please enter a valid command.")
            return

        bot.send_message(message.chat.id, f"Please upload the video for the command {command}.")
        bot.register_next_step_handler(message, lambda msg: attach_video_to_command(msg, command))
    except IndexError:
        bot.reply_to(message, "Please specify a command.")

def attach_video_to_command(message, command):
    video_file_id = message.video.file_id

    cursor.execute("INSERT INTO command_videos (command, video_file_id) VALUES (%s, %s) ON CONFLICT (command) DO UPDATE SET video_file_id = %s", (command, video_file_id, video_file_id))
    conn.commit()

    bot.reply_to(message, f"Video has been attached to the command {command}.")

# Enhanced Marketplace: Listing, Viewing, Approving Items, and Viewing Details
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
        item_name, item_description, item_price = map(str.strip, message.text.split(','))
        item_id = str(uuid.uuid4())

        cursor.execute("""
            INSERT INTO marketplace (item_id, name, description, price, seller_id, status)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (item_id, item_name, item_description, item_price, user_id, 'pending_approval' if 'iphone' in item_name.lower() else 'available'))
        conn.commit()

        bot.send_message(user_id, f"Item '{item_name}' has been listed successfully with ID: {item_id}. Please note that a 25% commission will be deducted from the selling price.")

        if 'iphone' in item_name.lower():
            for admin_id in ADMIN_IDS:
                keyboard = types.InlineKeyboardMarkup()
                approve_button = types.InlineKeyboardButton("✅ Approve Listing", callback_data=f"approve_{item_id}")
                decline_button = types.InlineKeyboardButton("❌ Decline Listing", callback_data=f"decline_{item_id}")
                keyboard.add(approve_button, decline_button)
                bot.send_message(admin_id, f"User {user_id} has listed a sensitive item '{item_name}'.", reply_markup=keyboard)
        else:
            bot.send_message(user_id, f"Your item '{item_name}' is now available in the marketplace.")
    except ValueError:
        bot.send_message(user_id, "Invalid format. Please try again using the format: Name, Description, Price.")

@bot.callback_query_handler(func=lambda call: call.data.startswith("approve_") or call.data.startswith("decline_"))
def handle_item_approval(call):
    admin_id = call.message.chat.id
    item_id = call.data.split("_")[1]

    if call.data.startswith("approve_"):
        cursor.execute("UPDATE marketplace SET status = 'available' WHERE item_id = %s", (item_id,))
        conn.commit()

        cursor.execute("SELECT seller_id FROM marketplace WHERE item_id = %s", (item_id,))
        seller_id = cursor.fetchone()[0]
        bot.send_message(seller_id, f"Your item '{marketplace_data[item_id]['name']}' has been approved by an admin and is now available for purchase.")
        bot.send_message(admin_id, f"Item {item_id} has been approved and is now available in the marketplace.")
    elif call.data.startswith("decline_"):
        cursor.execute("DELETE FROM marketplace WHERE item_id = %s", (item_id,))
        conn.commit()

        cursor.execute("SELECT seller_id FROM marketplace WHERE item_id = %s", (item_id,))
        seller_id = cursor.fetchone()[0]
        bot.send_message(seller_id, f"Your item '{marketplace_data[item_id]['name']}' was declined by an admin. Please contact support for more information.")
        bot.send_message(admin_id, f"Item {item_id} has been declined and removed from the marketplace.")

@bot.message_handler(commands=['view_items'])
def view_items(message):
    cursor.execute("SELECT item_id, name, price FROM marketplace WHERE status = 'available'")
    items = cursor.fetchall()

    if not items:
        bot.reply_to(message, "No items listed yet.")
        return

    items_text = "📦 *Marketplace Items:*\n\n"
    for item_id, name, price in items:
        items_text += f"ID: {item_id}\nName: {name}\nPrice: {price} INR\n\n"

    bot.send_message(message.chat.id, items_text, parse_mode='Markdown')

@bot.message_handler(commands=['view_item'])
def view_item(message):
    bot.send_message(message.chat.id, "Please send the ID of the item you wish to view.")
    bot.register_next_step_handler(message, show_item_details)

def show_item_details(message):
    item_id = message.text.strip()
    cursor.execute("SELECT name, description, price, status FROM marketplace WHERE item_id = %s", (item_id,))
    item = cursor.fetchone()

    if not item or item[3] !='available':
        bot.reply_to(message, "This item is no longer available.")
        return

    name, description, price, _ = item
    admin_username = "@sale2xx"  # Admin username that will handle item purchases

    item_details = (
        f"📦 *Item Details:*\n\n"
        f"Name: {name}\n"
        f"Description: {description}\n"
        f"Price: {price} INR\n\n"
        f"To purchase this item, please contact the admin: {admin_username}"
    )
    bot.send_message(message.chat.id, item_details, parse_mode='Markdown')

# Admin command to show the number of users and customers
@bot.message_handler(commands=['stats'])
def stats(message):
    if message.chat.id not in ADMIN_IDS:
        bot.reply_to(message, "You are not authorized to view stats.")
        return

    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM users WHERE subscription_active = TRUE")
    active_subscribers = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM users WHERE status = 'free_user'")
    free_users = cursor.fetchone()[0]

    stats_text = (
        f"📊 *Bot Statistics:*\n\n"
        f"Total Users: {total_users}\n"
        f"Active Subscribers: {active_subscribers}\n"
        f"Free Users: {free_users}\n"
    )
    bot.send_message(message.chat.id, stats_text, parse_mode='Markdown')

# Help command to assist users
@bot.message_handler(commands=['help'])
def help_command(message):
    help_text = (
        "👋 *Help and Support*\n\n"
        "For any issues, please contact us or join our support group.\n\n"
        "Use /feedback to report any issues or provide feedback."
    )
    bot.send_message(message.chat.id, help_text, parse_mode='Markdown')

# Feedback command to collect user feedback
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

# Support command to link to the support group
@bot.message_handler(commands=['support'])
def support(message):
    support_group_link = "https://t.me/your_support_group"  # Replace with your actual support group link
    support_text = (
        "🚑 *Support Group*\n\n"
        "If you need help or have any questions, join our support group here:\n"
        f"[Join Support Group]({support_group_link})"
    )
    bot.send_message(message.chat.id, support_text, parse_mode='Markdown')

# Enhanced prediction system
@bot.message_handler(commands=['set_interval'])
def set_interval(message):
    user_id = message.chat.id
    cursor.execute("SELECT subscription_active FROM users WHERE user_id = %s", (user_id,))
    user = cursor.fetchone()
    if not user or not user[0]:
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

        cursor.execute("UPDATE users SET interval = %s WHERE user_id = %s", (interval, user_id))
        conn.commit()

        bot.send_message(user_id, f"Prediction interval set to {interval} minutes.")
        real_time_prediction(user_id)
    except ValueError:
        bot.reply_to(user_id, "Please enter a valid number for the interval.")

# Admin command to remove users
@bot.message_handler(commands=['remove_user'])
def remove_user(message):
    if message.chat.id not in ADMIN_IDS:
        bot.reply_to(message, "You are not authorized to remove users.")
        return

    try:
        _, user_id = message.text.split()
        user_id = int(user_id)
        cursor.execute("DELETE FROM users WHERE user_id = %s", (user_id,))
        conn.commit()

        bot.reply_to(message, f"User {user_id} has been removed from the bot.")
    except ValueError:
        bot.reply_to(message, "Usage: /remove_user <user_id>")

# Function to handle unrecognized commands and show help
@bot.message_handler(func=lambda message: True)
def fallback(message):
    bot.reply_to(message, "I'm sorry, I didn't understand that command. Use /help to see the available commands.")

# Start the bot polling
if __name__ == "__main__":
    try:
        bot.polling(none_stop=True)
    except Exception as e:
        logging.error(f"Bot polling failed: {e}")
        bot.stop_polling()
        scheduler.shutdown()


import telebot
import requests
import razorpay
import stripe

# Initialize the bot with the Telegram API token
bot = telebot.TeleBot("6736371777:AAE1I-Blq7ZU5e-KSOeKLvzpD89zybfWueg")

# List of cryptocurrencies to track
CRYPTO_LIST = ["bitcoin", "ethereum", "litecoin", "ripple"]

# Initialize Razorpay and Stripe clients with your credentials
razorpay_client = razorpay.Client(auth=("rzp_test_XXXXXXX", "XXXXXXXXXXXX"))
stripe.api_key = "sk_test_XXXXXXXXXXXX"

# Admin user ID for security
ADMIN_ID = 123456789  # Replace with your actual Telegram user ID

def prediction():
    prediction_text = ""
    for crypto in CRYPTO_LIST:
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
        except Exception as e:
            prediction_text += f"Error fetching data for {crypto}: {str(e)}\n"
    return prediction_text

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "Welcome! Subscribe for crypto trading predictions. Use /subscribe to choose a subscription plan.")

@bot.message_handler(commands=['subscribe'])
def subscribe(message):
    keyboard = telebot.types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    button_1 = telebot.types.KeyboardButton(text="250 INR (Razorpay)")
    button_2 = telebot.types.KeyboardButton(text="$10 (Stripe)")
    keyboard.add(button_1, button_2)
    bot.reply_to(message, "Choose a subscription option:", reply_markup=keyboard)

@bot.message_handler(func=lambda message: message.text in ["250 INR (Razorpay)", "$10 (Stripe)"])
def payment_processing(message):
    if message.text == "250 INR (Razorpay)":
        order = razorpay_client.order.create(dict(amount=25000, currency="INR", payment_capture=1))
        payment_link = f"https://rzp.io/l/{order['id']}"
        bot.reply_to(message, f"Please pay using this link: {payment_link}")
    elif message.text == "$10 (Stripe)":
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
    
    # Here you might want to wait for payment confirmation before providing predictions.
    # This is where you would normally integrate payment confirmation logic.

@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.from_user.id == ADMIN_ID:
        keyboard = telebot.types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
        button_1 = telebot.types.KeyboardButton(text="Change Subscription Price")
        button_2 = telebot.types.KeyboardButton(text="Send Announcement")
        keyboard.add(button_1, button_2)
        bot.reply_to(message, "Admin Panel", reply_markup=keyboard)

@bot.message_handler(func=lambda message: message.text == "Change Subscription Price")
def change_price(message):
    if message.from_user.id == ADMIN_ID:
        bot.reply_to(message, "Enter new price (e.g., 250 INR or $10):")
        bot.register_next_step_handler(message, update_price)

def update_price(message):
    new_price = message.text
    bot.reply_to(message, f"Price updated to {new_price}")

@bot.message_handler(func=lambda message: message.text == "Send Announcement")
def send_announcement(message):
    if message.from_user.id == ADMIN_ID:
        bot.reply_to(message, "Enter announcement text:")
        bot.register_next_step_handler(message, broadcast_announcement)

def broadcast_announcement(message):
    announcement_text = message.text
    # Broadcast the message to all users; you'd need to keep a list of user_ids to send this to.
    bot.send_message(ADMIN_ID, announcement_text)
    bot.reply_to(message, "Announcement sent")

bot.polling()

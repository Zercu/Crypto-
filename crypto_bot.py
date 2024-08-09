
import telebot
import requests
import razorpay
import stripe

bot = telebot.TeleBot("6736371777:AAE1I-Blq7ZU5e-KSOeKLvzpD89zybfWueg")

CRYPTO_LIST = ["bitcoin", "ethereum", "litecoin", "ripple"]

# Razorpay setup
razorpay_client = razorpay.Client(auth=("YOUR_RAZORPAY_KEY_ID", "YOUR_RAZORPAY_KEY_SECRET"))

# Stripe setup
stripe.api_key = "YOUR_STRIPE_SECRET_KEY"

# Crypto trading prediction function
def prediction():
    prediction_text = ""
    for crypto in CRYPTO_LIST:
        current_price = requests.get(f"https://fcsapi.com/api-v3/crypto/latest?id=78&access_key=nDFgfOJUEHOZweVbJkt2JGu99").json()[crypto]["usd"]
        previous_price = current_price * 0.95
        percentage_change = ((current_price - previous_price) / previous_price) * 100
        if percentage_change > 0:
            prediction_text += f"{crypto.capitalize()}: Price is expected to increase by {percentage_change:.2f}%\n"
        else:
            prediction_text += f"{crypto.capitalize()}: Price is expected to decrease by {abs(percentage_change):.2f}%\n"
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
        # Create a Razorpay order
        order = razorpay_client.order.create(dict(amount=25000, currency="INR", payment_capture=1))
        bot.reply_to(message, f"Please pay using this link: {order['receipt']}")
    elif message.text == "$10 (Stripe)":
        # Create a Stripe checkout session
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{'price_data': {'currency': 'usd', 'unit_amount': 1000, 'product_data': {'name': 'Crypto Trading Predictions'}}, 'quantity': 1}],
            mode='payment',
            success_url='(link unavailable)',
            cancel_url='(link unavailable)',
        )
        bot.reply_to(message, f"Please pay using this link: {checkout_session.url}")
    # Call the prediction function and send the output to the user
    bot.reply_to(message, prediction())

bot.polling()
```


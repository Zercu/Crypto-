import telebot
import requests

bot = telebot.TeleBot("YOUR_TELEGRAM_BOT_TOKEN")

CRYPTO_LIST = ["bitcoin", "ethereum", "litecoin", "ripple"]

# Crypto trading prediction function
def prediction():
    prediction_text = ""

    for crypto in CRYPTO_LIST:
        current_price = requests.get(f"https://api.coingecko.com/api/v3/simple/price?ids={crypto}&vs_currencies=usd").json()[crypto]["usd"]
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

# Include other message handler functions

bot.polling()
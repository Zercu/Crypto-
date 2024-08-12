# Replace polling with webhook setup
WEBHOOK_URL = f"https://{your-heroku-app-name}.herokuapp.com/{your-telegram-token}/webhook"

@app.route(f'/{your-telegram-token}/webhook', methods=['POST'])
def webhook():
    json_string = request.get_data().decode('UTF-8')
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return '!', 200

bot.remove_webhook()
bot.set_webhook(url=WEBHOOK_URL)

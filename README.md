# Crypto Trading Telegram Bot with Flask and Razorpay Integration

This is a Python-based Telegram bot designed to provide cryptocurrency trading predictions, manage user subscriptions via Razorpay, and offer a basic marketplace for buying and selling items. The bot is integrated with a Flask web server and is intended to be deployed on Heroku.


## Deployment
   
[Visit the Heroku Deployment](https://your-app-name.herokuapp.com/)


## Commands

### General User Commands

- **`/start`**: 
  - Initializes the bot and welcomes the user. Provides options for subscribing to the prediction service or accessing the marketplace.
  
- **`/subscribe`**: 
  - Subscribe to the real-time prediction service. Options include 250 INR via Razorpay, with future support for PayPal.
  
- **`/set_interval`**: 
  - Set the interval for receiving predictions. Options range from 1 to 5 minutes.

- **`/feedback`**: 
  - Send feedback or report any issues with the bot. The feedback is sent to the admin for review.

- **`/help`**: 
  - Display a help message with a list of available commands.

- **`/marketplace`**: 
  - Access the marketplace to list items or view items for sale.

### Admin Commands

- **`/admin`**: 
  - Access the admin panel. Available only to users with admin privileges.

- **`Change Subscription Price`**: 
  - Change the subscription price for the prediction service. This command is accessed through the admin panel.

- **`Send Announcement`**: 
  - Send an announcement to all users. This command is accessed through the admin panel.

- **`View Subscriptions`**: 
  - View current active subscriptions. This command is accessed through the admin panel.

### Marketplace Commands

- **`List Item`**: 
  - List an item for sale in the marketplace. The user must provide the item name, description, price in INR, and UPI ID.

- **`View Items`**: 
  - View all items currently listed in the marketplace.

- **`/confirm <item_token>`**: 
  - Confirm the sale of an item as a seller using the unique item token.

## How It Works

1. **Crypto Predictions**:
   - The bot uses technical indicators like Moving Averages, RSI, and Bollinger Bands to generate predictions. Users can react to predictions with "🔼 Up Tick" or "🔻 Down Tick".

2. **Marketplace**:
   - Users can list items with details and a UPI ID. When a buyer makes a purchase, they provide the UPI transaction ID for verification. The seller confirms the sale, and the bot processes the payment (with a 25% commission).

3. **Subscriptions**:
   - Users can subscribe to the prediction service through Razorpay. The bot automatically handles the subscription duration and sends predictions at the selected interval.

4. **Admin Panel**:
   - Admins can manage subscription prices, send announcements, and view subscriptions. These features ensure that the service remains flexible and responsive to user needs.

## Deployment

To deploy this bot on Heroku:

1. **Create a `Procfile`** in your repository:
   ```text
   worker: python bot.py

## Features

- **Cryptocurrency Price Predictions**: 
  - Fetches historical price data for various cryptocurrencies using the CoinGecko API.
  - Performs advanced technical analysis using TA-Lib indicators like Moving Averages, RSI, and Bollinger Bands.
  - Provides users with real-time buy, sell, or hold recommendations based on the analysis.

- **Subscription Management**:
  - Users can subscribe to receive real-time cryptocurrency predictions by making payments through Razorpay.
  - Handles payment processing with success and cancel URLs.

- **Marketplace**:
  - Users can list items for sale and make purchases within a simple marketplace system.
  - Payment verification and notifications for buyers and sellers.

- **Admin Features**:
  - Special commands for admins to manage subscriptions, prices, and announcements.

- **Webhook-Based Updates**:
  - Efficient handling of Telegram updates using webhooks for better performance on Heroku.

## Prerequisites

- Python 3.7+
- Telegram Bot API Token (from BotFather)
- Razorpay API Keys
- Heroku Account

## Setup Instructions

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/your-repo-name.git
cd your-repo-name


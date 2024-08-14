To deploy the bot on an Ubuntu VPS through GitHub, you can follow these detailed steps:

### 1. **Initial Setup on Your VPS**

1. **Log in to your VPS**: Use SSH to connect to your VPS.
   ```sh
   ssh your-username@your-vps-ip-address
   ```

2. **Update and Upgrade the System**:
   ```sh
   sudo apt-get update && sudo apt-get upgrade -y
   ```

3. **Install Required Software**:
   - **Python 3.x**: Ensure Python is installed.
   ```sh
   sudo apt-get install python3 python3-pip python3-venv git -y
   ```

### 2. **Set Up the Project**

1. **Clone Your GitHub Repository**:
   ```sh
   git clone https://github.com/yourusername/your-bot-project.git
   cd your-bot-project
   ```

2. **Create a Virtual Environment**:
   - **Optional but Recommended**: This keeps your project dependencies isolated.
   ```sh
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install Dependencies**:
   ```sh
   pip install -r requirements.txt
   ```

4. **Create and Configure the `.env` File**:
   - Copy the `.env.example` if it exists, or create a new `.env` file with your bot's credentials.
   ```sh
   cp .env.example .env
   nano .env
   ```
   - Add your environment variables (replace with your actual values):
   ```dotenv
   TELEGRAM_BOT_TOKEN="your-telegram-bot-token"
   ADMIN_IDS="123456789,987654321"
   GROUP_CHAT_ID="your-group-chat-id"
   UPI_ID="your-upi-id"
   ```

### 3. **Running the Bot**

1. **Run the Bot Manually**:
   - Ensure you are in your project directory and the virtual environment is activated:
   ```sh
   source venv/bin/activate
   python3 app.py
   ```

   - **Note**: Running the bot this way will stop it if the terminal session is closed. To keep the bot running in the background, use tools like `screen`, `tmux`, or `nohup`.

2. **Run the Bot in the Background (Using `nohup`)**:
   ```sh
   nohup python3 app.py &
   ```

   - This command runs the bot in the background, redirecting output to a file called `nohup.out`.

### 4. **Setting Up the Bot to Start on System Boot**

1. **Using `systemd` to Create a Service**:

   - **Create a new service file**: `/etc/systemd/system/yourbot.service`
   ```sh
   sudo nano /etc/systemd/system/yourbot.service
   ```

   - **Add the following configuration**:
   ```ini
   [Unit]
   Description=Telegram Bot Service
   After=network.target

   [Service]
   User=your-username
   WorkingDirectory=/path/to/your-bot-project
   ExecStart=/path/to/your-bot-project/venv/bin/python3 /path/to/your-bot-project/app.py
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```

   Replace `/path/to/your-bot-project` with the full path to your project directory and `your-username` with your actual username.

2. **Enable and Start the Service**:

   - **Reload `systemd` to recognize the new service**:
   ```sh
   sudo systemctl daemon-reload
   ```

   - **Start the bot service**:
   ```sh
   sudo systemctl start yourbot
   ```

   - **Enable the service to start on boot**:
   ```sh
   sudo systemctl enable yourbot
   ```

3. **Check Service Status**:
   ```sh
   sudo systemctl status yourbot
   ```

   - This will show you the status of your bot service and any errors if it failed to start.

### 5. **Managing the Bot**

- **Start the Bot**:
  ```sh
  sudo systemctl start yourbot
  ```

- **Stop the Bot**:
  ```sh
  sudo systemctl stop yourbot
  ```

- **Restart the Bot**:
  ```sh
  sudo systemctl restart yourbot
  ```

- **View Logs**:
  ```sh
  sudo journalctl -u yourbot.service -f
  ```

### 6. **Updating the Bot**

To update your bot with changes from GitHub:

1. **Pull the Latest Changes**:
   ```sh
   cd /path/to/your-bot-project
   git pull origin main
   ```

2. **Restart the Bot**:
   ```sh
   sudo systemctl restart yourbot
   ```

### Summary

- **Environment Setup**: Python, pip, virtual environment, Git.
- **Deployment**: Clone your GitHub repository, set up the bot using a virtual environment, and manage the bot using `systemd` for automatic startup and reliability.
- **Management**: Control the bot with `systemctl` commands and monitor its status.

This setup ensures your bot runs smoothly on your Ubuntu VPS, and it can automatically restart if your server reboots or if the bot encounters an error.
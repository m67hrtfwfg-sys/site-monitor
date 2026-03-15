# Site Monitor

A simple Python service that monitors websites and sends alerts via Telegram.

## Features

- Monitor multiple websites
- Send Telegram alerts when a site goes down
- Async monitoring using aiohttp
- Docker support

## Setup

1. Clone the repository

git clone https://github.com/yourname/site-monitor

2. Install dependencies

pip install -r requirements.txt

3. Create .env file

TELEGRAM_TOKEN=your_token
CHAT_ID=your_chat_id

4. Run the monitor

python monitor.py --interval 60

## Docker

docker build -t site-monitor .
docker run --env-file .env site-monitor

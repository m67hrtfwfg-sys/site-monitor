import os
import asyncio
import aiohttp
import argparse
import time
import json
import logging
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv
from datetime import datetime


load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "60"))
TIMEOUT = int(os.getenv("TIMEOUT", "5"))

if not TELEGRAM_TOKEN or not CHAT_ID:
    raise RuntimeError("Telegram ENV variables are not set")

STATE_FILE = "data/last_state.json"
LOG_FILE = "monitor.log"



def setup_logger():
    logger = logging.getLogger("site_monitor")
    logger.setLevel(logging.INFO)

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s"
    )

    console = logging.StreamHandler()
    console.setFormatter(formatter)

    file_handler = RotatingFileHandler(
        LOG_FILE, maxBytes=1_000_000, backupCount=3
    )
    file_handler.setFormatter(formatter)

    logger.addHandler(console)
    logger.addHandler(file_handler)

    return logger


logger = setup_logger()



def load_last_state():
    if not os.path.exists(STATE_FILE):
        return {}
    with open(STATE_FILE, "r") as f:
        return json.load(f)


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)



async def send_telegram(session, message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message
    }
    async with session.post(url, data=payload):
        pass



async def check_site(session, site):
    url = site["url"]
    name = site["name"]
    threshold = site.get("threshold", 1)

    try:
        start = time.time()
        async with session.get(url, timeout=TIMEOUT) as response:
            response_time = round(time.time() - start, 2)

            if response.status != 200:
                status = "critical"
            elif response_time > threshold:
                status = "slow"
            else:
                status = "up"

            return name, {
                "status": status,
                "code": response.status,
                "time": response_time
            }

    except Exception as e:
        logger.error(f"{name} failed: {e}")
        return name, {
            "status": "critical",
            "code": 0,
            "time": 0
        }


async def check_all_sites(sites):
    async with aiohttp.ClientSession() as session:
        tasks = [check_site(session, site) for site in sites]
        results = await asyncio.gather(*tasks)
        return dict(results)



async def main_logic():
    sites = [
        {"name": "Google", "url": "https://google.com"},
        {"name": "GitHub", "url": "https://github.com"},
        {"name": "BadSite", "url": "https://example.invalid"},
    ]

    last_state = load_last_state()
    current_state = await check_all_sites(sites)

    async with aiohttp.ClientSession() as session:
        for name, data in current_state.items():
            last_status = last_state.get(name, {}).get("status")

            logger.info(
                f"{name} | {data['status']} | "
                f"code={data['code']} | time={data['time']}s"
            )

            if last_status != data["status"]:
                icon = "🟢" if data["status"] == "up" else \
                       "⚠️" if data["status"] == "slow" else "🚨"

                message = (
                    f"{icon} STATUS CHANGED\n"
                    f"Site: {name}\n"
                    f"Status: {data['status']}\n"
                    f"HTTP: {data['code']}\n"
                    f"Response: {data['time']}s"
                )

                await send_telegram(session, message)

    save_state(current_state)


    
def parse_args():
    parser = argparse.ArgumentParser(
        description="Async Site Monitoring Service"
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run checks once and exit"
    )
    parser.add_argument(
        "--interval",
        type=int,
        help="Run checks every N seconds"
    )
    return parser.parse_args()



async def run_once():
    await main_logic()


async def run_interval(interval):
    while True:
        await main_logic()
        await asyncio.sleep(interval)


if __name__ == "__main__":
    args = parse_args()

    if args.once:
        asyncio.run(run_once())
    else:
        interval = args.interval or CHECK_INTERVAL
        asyncio.run(run_interval(interval))
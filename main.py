import logging
import logging.handlers
import os
from telegram.ext import Defaults, ApplicationBuilder
from telegram.constants import ParseMode
from telegram.ext import AIORateLimiter
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)

logHandler = logging.handlers.TimedRotatingFileHandler(
    'logs/diamond', when='D', interval=1, backupCount=10)
logHandler.suffix = '%Y-%m-%d.log'
logHandler.setFormatter(logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
logger = logging.getLogger()
logger.addHandler(logHandler)

from src.setup import setup


BOT_TOKEN = os.getenv("BOT_TOKEN")
ENV_MODE = os.getenv("MODE")
WEBHOOK_HOST = os.getenv("WEBHOOK_HOST")
WEBHOOK_PORT = int(os.getenv("WEBHOOK_PORT", "8443"))


def main():
    defualts = Defaults(parse_mode=ParseMode.HTML)

    application = ApplicationBuilder().token(
        BOT_TOKEN).post_init(setup).defaults(defualts).rate_limiter(AIORateLimiter()).build()

    match ENV_MODE.lower():
        case 'development':
            application.run_polling()
        case 'production':
            if not WEBHOOK_HOST:
                raise ValueError("WEBHOOK_HOST is required in production mode")
            webhook_url = f"https://{WEBHOOK_HOST}:{WEBHOOK_PORT}"

            application.run_webhook(
                webhook_url=webhook_url,
                port=WEBHOOK_PORT,
                listen="0.0.0.0",
            )


if __name__ == "__main__":
    main()

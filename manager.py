import os
import asyncio
from dotenv import load_dotenv
from core.logger import log
from bot.client import BotManager
from core.utils import get_feedback

# Load environment secrets
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

if __name__ == "__main__":
    # Force SelectorEventLoop on Windows to fix Gateway handshake hangs with modern Python
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        log.info("[Bootstrap] Event loop policy set to WindowsSelectorEventLoopPolicy.")

    # Initialize modular BotManager
    bot = BotManager()

    if TOKEN:
        bot.run(TOKEN)
    else:
        log.error(get_feedback(bot.i18n, "error_no_token"))

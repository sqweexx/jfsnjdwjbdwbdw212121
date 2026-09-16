import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID", "0"))
TIMEZONE = os.getenv("TIMEZONE", "Europe/Prague")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is required")
if not OWNER_ID:
    raise ValueError("OWNER_ID is required")

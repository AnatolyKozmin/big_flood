import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is not set in environment variables")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL is not set in environment variables")


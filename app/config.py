"""Central place to read configuration from environment variables.

Loading everything here (instead of calling os.getenv all over the code) keeps
the rest of the app clean and makes it obvious what the MVP depends on.
"""
import os
from dotenv import load_dotenv

load_dotenv()  # reads a local .env file if present


class Config:
    # LINE
    LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET", "")
    LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")

    # LLM (DeepSeek)
    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
    DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash")
    DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")

    # Google Sheets
    GOOGLE_SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "service_account.json")
    GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID", "")
    GOOGLE_WORKSHEET_NAME = os.getenv("GOOGLE_WORKSHEET_NAME", "workouts")


config = Config()

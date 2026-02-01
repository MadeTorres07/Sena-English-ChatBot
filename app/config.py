# Configuración

import os
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Telegram
    TELEGRAM_BOT_TOKEN: str
    WEBHOOK_URL: Optional[str] = None
    
    # Groq AI
    GROQ_API_KEY: str
    GROQ_MODEL: str = "llama-3.1-70b-versatile"
    
    # Google Sheets
    GOOGLE_SHEETS_CREDENTIALS: dict = {}
    SPREADSHEET_ID: str
    
    # App
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    
    class Config:
        env_file = ".env"

settings = Settings()
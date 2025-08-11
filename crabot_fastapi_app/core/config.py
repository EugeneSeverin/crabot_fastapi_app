from dotenv import load_dotenv
import os

load_dotenv()

class Settings:
    LOG_LEVEL = os.getenv("NEZKA_LOG_LEVEL", 'INFO')


settings = Settings()


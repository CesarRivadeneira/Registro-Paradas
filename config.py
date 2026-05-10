from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///mantenimiento.db")
APP_PORT = int(os.getenv("APP_PORT", "8501"))
APP_HOST = os.getenv("APP_HOST", "0.0.0.0")
SECRET_KEY = os.getenv("SECRET_KEY", "dev-key-change-me")

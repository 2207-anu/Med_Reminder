import os
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

def get_secret(key, default=""):
    try:
        return st.secrets[key]
    except (KeyError, FileNotFoundError):
        return os.getenv(key, default)

SECRET_KEY = get_secret("SECRET_KEY", "medremind-dev-secret-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24

DB_CONFIG = {
    "host": get_secret("DB_HOST", "localhost"),
    "port": int(get_secret("DB_PORT", "5432")),
    "dbname": get_secret("DB_NAME", "medicine_app"),
    "user": get_secret("DB_USER", "postgres"),
    "password": get_secret("DB_PASSWORD", "asdfghjkl"),
    "sslmode": get_secret("DB_SSLMODE", "require"),
}

GMAIL_USER = get_secret("GMAIL_USER", "")
GMAIL_PASS = get_secret("GMAIL_PASS", "")

API_KEYS = [k for k in [
    get_secret("GEMINI_API_KEY_1"),
    get_secret("GEMINI_API_KEY_2"),
    get_secret("GEMINI_API_KEY_3"),
] if k]
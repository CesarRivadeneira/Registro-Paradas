from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///mantenimiento.db")

# Streamlit Cloud override via st.secrets
try:
    import streamlit as st
    secrets_url = st.secrets.get("DATABASE_URL")
    if secrets_url:
        DATABASE_URL = secrets_url
except Exception:
    pass

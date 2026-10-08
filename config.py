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

SECRET_KEY = os.getenv("SECRET_KEY", "")

# Streamlit Cloud override via st.secrets
if not SECRET_KEY:
    try:
        import streamlit as st
        SECRET_KEY = st.secrets.get("SECRET_KEY", "")
    except Exception:
        pass

if not SECRET_KEY:
    SECRET_KEY = "clave-no-configurada"

SECRET_KEY_POR_DEFECTO = SECRET_KEY in ("mi-clave-secreta-cambiame", "clave-no-configurada")
if SECRET_KEY_POR_DEFECTO:
    print("AVISO: SECRET_KEY usa un valor por defecto. Configurala en .env o en los secrets de Streamlit Cloud.")
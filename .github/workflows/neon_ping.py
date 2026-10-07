import os
import sys

url = os.environ.get("DATABASE_URL", "")
if not url:
    sys.exit(0)

# Acepta los dialéctos `postgresql+psycopg2://` y `postgresql+psycopg://`
url = url.replace("postgresql+psycopg2://", "postgresql://")
url = url.replace("postgresql+psycopg://", "postgresql://")

import psycopg2

try:
    conn = psycopg2.connect(url, connect_timeout=10)
    with conn.cursor() as cur:
        cur.execute("SELECT 1")
        cur.fetchone()
    conn.close()
    print("Neon ping OK")
except Exception as exc:
    print(f"Neon ping failed: {exc}")
    sys.exit(1)
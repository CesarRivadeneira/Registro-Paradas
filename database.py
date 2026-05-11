import hashlib
import os
import base64
import time
from contextlib import contextmanager
from datetime import datetime

import streamlit as st
from sqlalchemy import create_engine, text, func
from sqlalchemy.orm import sessionmaker, joinedload
from sqlalchemy.exc import OperationalError

from config import DATABASE_URL
from models import Base, Sector, Linea, Equipo, Repuesto, Usuario, EventoMantenimiento

engine = create_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    connect_args={"connect_timeout": 10},
)
SessionLocal = sessionmaker(bind=engine)


def init_db():
    max_attempts = 3
    for attempt in range(1, max_attempts + 1):
        try:
            Base.metadata.create_all(bind=engine)
            _migrar_base()
            return
        except OperationalError as e:
            if attempt < max_attempts:
                time.sleep(2 * attempt)
            else:
                raise RuntimeError(
                    f"No se pudo conectar a la base de datos tras {max_attempts} intentos: {e}"
                ) from e


def _migrar_base():
    """Agrega columnas nuevas si no existen (migración progresiva)."""
    with get_db() as db:
        dialect = db.bind.dialect.name

        if _migracion_ya_aplicada(db, dialect):
            return

        columnas = [
            ("eventos", "user_id", "INTEGER REFERENCES usuarios(id)"),
            ("eventos", "hora_inicio", "VARCHAR DEFAULT ''"),
            ("eventos", "duracion_minutos", "INTEGER DEFAULT 0"),
            ("equipos", "linea_id", "INTEGER REFERENCES lineas(id)"),
        ]

        for table, col, definition in columnas:
            try:
                if dialect == "sqlite":
                    conn = db.connection().connection
                    cursor = conn.cursor()
                    cursor.execute(
                        f"ALTER TABLE {table} ADD COLUMN {col} {definition}"
                    )
                elif dialect == "postgresql":
                    db.execute(
                        text(
                            f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {col} {definition}"
                        )
                    )
                    db.commit()
            except Exception:
                pass

        if dialect == "sqlite":
            _migrar_equipos_sector_a_linea(db)

        _crear_indices(db, dialect)


def _crear_indices(db, dialect):
    indices = [
        "CREATE INDEX IF NOT EXISTS ix_eventos_equipo_id ON eventos(equipo_id)",
        "CREATE INDEX IF NOT EXISTS ix_eventos_fecha ON eventos(fecha)",
        "CREATE INDEX IF NOT EXISTS ix_lineas_sector_id ON lineas(sector_id)",
    ]
    for idx in indices:
        try:
            db.execute(text(idx))
            db.commit()
        except Exception:
            pass


def _migracion_ya_aplicada(db, dialect):
    """Retorna True si las columnas nuevas ya existen (migración previa)."""
    try:
        if dialect == "postgresql":
            result = db.execute(
                text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_name='eventos' AND column_name='user_id'"
                )
            ).fetchone()
            return result is not None
        elif dialect == "sqlite":
            conn = db.connection().connection
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(eventos)")
            cols = {row[1] for row in cursor.fetchall()}
            return "user_id" in cols
    except Exception:
        pass
    return False


def _migrar_equipos_sector_a_linea(db):
    """Migra equipos viejos que usaban sector_id al nuevo esquema con linea_id."""
    try:
        conn = db.connection().connection
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM equipos WHERE linea_id IS NULL AND sector_id IS NOT NULL")
        if cursor.fetchone()[0] == 0:
            return
        cursor.execute("SELECT DISTINCT sector_id FROM equipos WHERE linea_id IS NULL AND sector_id IS NOT NULL")
        sectores = cursor.fetchall()
        for (sector_id,) in sectores:
            sector = db.query(Sector).get(sector_id)
            if not sector:
                continue
            linea = db.query(Linea).filter(Linea.nombre == sector.nombre, Linea.sector_id == sector_id).first()
            if not linea:
                linea = Linea(nombre=sector.nombre, sector_id=sector_id)
                db.add(linea)
                db.flush()
            db.query(Equipo).filter(
                Equipo.sector_id == sector_id, Equipo.linea_id.is_(None)
            ).update({Equipo.linea_id: linea.id})
        db.commit()
    except Exception:
        db.rollback()


# =====================================
# PASSWORD UTILS
# =====================================

def hash_password(password: str) -> str:
    salt = os.urandom(32)
    key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100000)
    return base64.b64encode(salt + key).decode()


def verificar_password(password: str, stored: str) -> bool:
    try:
        data = base64.b64decode(stored)
        salt = data[:32]
        key = data[32:]
        new_key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100000)
        return key == new_key
    except Exception:
        return False


@contextmanager
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# =====================================
# CRUD SECTORES
# =====================================

def crear_sector(nombre):
    with get_db() as db:
        existe = db.query(Sector).filter(Sector.nombre == nombre).first()
        if not existe:
            db.add(Sector(nombre=nombre))
            db.commit()
    st.cache_data.clear()


@st.cache_data(ttl=60)
def obtener_sectores():
    with get_db() as db:
        return db.query(Sector).all()


def eliminar_sector(sector_id):
    with get_db() as db:
        sector = db.query(Sector).get(sector_id)
        if sector:
            db.query(Linea).filter(Linea.sector_id == sector_id).delete()
            db.delete(sector)
            db.commit()
    st.cache_data.clear()


# =====================================
# CRUD LINEAS
# =====================================

def crear_linea(nombre, sector_id):
    with get_db() as db:
        existe = db.query(Linea).filter(
            Linea.nombre == nombre, Linea.sector_id == sector_id
        ).first()
        if not existe:
            db.add(Linea(nombre=nombre, sector_id=sector_id))
            db.commit()
    st.cache_data.clear()


@st.cache_data(ttl=60)
def obtener_lineas():
    with get_db() as db:
        return db.query(Linea).options(joinedload(Linea.sector)).all()


@st.cache_data(ttl=60)
def obtener_lineas_por_sector(sector_id):
    with get_db() as db:
        return db.query(Linea).filter(Linea.sector_id == sector_id).all()


def eliminar_linea(linea_id):
    with get_db() as db:
        linea = db.query(Linea).get(linea_id)
        if linea:
            db.query(Equipo).filter(Equipo.linea_id == linea_id).delete()
            db.delete(linea)
            db.commit()
    st.cache_data.clear()


# =====================================
# CRUD EQUIPOS
# =====================================

def crear_equipo(nombre, tipo, linea_id):
    with get_db() as db:
        db.add(Equipo(nombre=nombre, tipo=tipo, linea_id=linea_id))
        db.commit()
    st.cache_data.clear()


@st.cache_data(ttl=60)
def obtener_equipos():
    with get_db() as db:
        return (
            db.query(Equipo)
            .options(joinedload(Equipo.linea).joinedload(Linea.sector))
            .all()
        )


@st.cache_data(ttl=60)
def obtener_equipos_por_linea(linea_id):
    with get_db() as db:
        return (
            db.query(Equipo)
            .filter(Equipo.linea_id == linea_id)
            .options(joinedload(Equipo.linea).joinedload(Linea.sector))
            .all()
        )


def eliminar_equipo(equipo_id):
    with get_db() as db:
        equipo = db.query(Equipo).get(equipo_id)
        if equipo:
            db.query(EventoMantenimiento).filter(
                EventoMantenimiento.equipo_id == equipo_id
            ).delete()
            db.delete(equipo)
            db.commit()
    st.cache_data.clear()


# =====================================
# CRUD REPUESTOS
# =====================================

def crear_repuesto(nombre, codigo, stock):
    with get_db() as db:
        try:
            existente = (
                db.query(Repuesto)
                .filter(Repuesto.codigo == codigo)
                .first()
            )
            if existente:
                existente.stock += stock
                db.commit()
                st.cache_data.clear()
                return True, "Stock actualizado correctamente"
            nuevo = Repuesto(nombre=nombre, codigo=codigo, stock=stock)
            db.add(nuevo)
            db.commit()
            st.cache_data.clear()
            return True, "Repuesto creado correctamente"
        except Exception as e:
            db.rollback()
            return False, str(e)


@st.cache_data(ttl=60)
def obtener_repuestos():
    with get_db() as db:
        return db.query(Repuesto).all()


# =====================================
# CRUD USUARIOS
# =====================================

def crear_usuario(username, password, nombre_completo="", rol="tecnico"):
    with get_db() as db:
        existe = db.query(Usuario).filter(Usuario.username == username).first()
        if existe:
            return False, "El usuario ya existe"
        usuario = Usuario(
            username=username,
            password_hash=hash_password(password),
            nombre_completo=nombre_completo,
            rol=rol,
        )
        db.add(usuario)
        db.commit()
    st.cache_data.clear()
    return True, "Usuario creado correctamente"


def autenticar(username, password):
    with get_db() as db:
        usuario = db.query(Usuario).filter(
            Usuario.username == username, Usuario.activo == True
        ).first()
        if usuario and verificar_password(password, usuario.password_hash):
            return usuario
        return None


@st.cache_data(ttl=60)
def obtener_usuarios():
    with get_db() as db:
        return db.query(Usuario).all()


def hay_usuarios():
    with get_db() as db:
        return db.query(Usuario).count() > 0


def desactivar_usuario(user_id):
    with get_db() as db:
        user = db.query(Usuario).get(user_id)
        if user:
            user.activo = not user.activo
            db.commit()
    st.cache_data.clear()


# =====================================
# CRUD EVENTOS
# =====================================

def crear_evento(equipo_id, falla, accion, repuesto_id, tecnico, observaciones, user_id=None, hora_inicio="", duracion_minutos=0):
    with get_db() as db:
        evento = EventoMantenimiento(
            equipo_id=equipo_id,
            falla=falla,
            accion=accion,
            repuesto_id=repuesto_id,
            tecnico=tecnico,
            observaciones=observaciones,
            user_id=user_id,
            hora_inicio=hora_inicio,
            duracion_minutos=duracion_minutos,
        )
        db.add(evento)
        if repuesto_id:
            repuesto = db.query(Repuesto).get(repuesto_id)
            if repuesto and repuesto.stock > 0:
                repuesto.stock -= 1
        db.commit()
    st.cache_data.clear()


def obtener_eventos():
    with get_db() as db:
        return (
            db.query(EventoMantenimiento)
            .options(
                joinedload(EventoMantenimiento.equipo)
                .joinedload(Equipo.linea)
                .joinedload(Linea.sector),
                joinedload(EventoMantenimiento.repuesto),
                joinedload(EventoMantenimiento.usuario),
            )
            .all()
        )


def obtener_eventos_recientes(limite=10):
    with get_db() as db:
        return (
            db.query(EventoMantenimiento)
            .options(
                joinedload(EventoMantenimiento.equipo)
                .joinedload(Equipo.linea)
                .joinedload(Linea.sector),
                joinedload(EventoMantenimiento.repuesto),
                joinedload(EventoMantenimiento.usuario),
            )
            .order_by(EventoMantenimiento.fecha.desc())
            .limit(limite)
            .all()
        )


@st.cache_data(ttl=60)
def contar_eventos_mes():
    inicio_mes = datetime.now().replace(
        day=1, hour=0, minute=0, second=0, microsecond=0
    )
    with get_db() as db:
        return (
            db.query(func.count(EventoMantenimiento.id))
            .filter(EventoMantenimiento.fecha >= inicio_mes)
            .scalar()
            or 0
        )


def obtener_resumen_dashboard():
    """Retorna DataFrame liviano para dashboard (evita cargar objetos ORM completos)."""
    import pandas as pd
    with get_db() as db:
        rows = (
            db.query(
                Sector.nombre.label("sector"),
                Linea.nombre.label("linea"),
                Equipo.nombre.label("equipo"),
                EventoMantenimiento.duracion_minutos,
            )
            .select_from(EventoMantenimiento)
            .join(Equipo, EventoMantenimiento.equipo_id == Equipo.id)
            .join(Linea, Equipo.linea_id == Linea.id)
            .join(Sector, Linea.sector_id == Sector.id)
            .all()
        )
    return pd.DataFrame(rows, columns=["sector", "linea", "equipo", "duracion_minutos"])


def contar_eventos_por_equipo():
    with get_db() as db:
        return (
            db.query(Equipo.nombre, func.count(EventoMantenimiento.id).label("total"))
            .join(EventoMantenimiento, Equipo.id == EventoMantenimiento.equipo_id)
            .group_by(Equipo.id)
            .order_by(func.count(EventoMantenimiento.id).desc())
            .all()
        )


def contar_eventos_por_sector():
    with get_db() as db:
        return (
            db.query(Sector.nombre, func.count(EventoMantenimiento.id).label("total"))
            .join(Linea, Linea.sector_id == Sector.id)
            .join(Equipo, Equipo.linea_id == Linea.id)
            .join(EventoMantenimiento, EventoMantenimiento.equipo_id == Equipo.id)
            .group_by(Sector.id)
            .order_by(func.count(EventoMantenimiento.id).desc())
            .all()
        )


def repuestos_bajo_stock(limite=5):
    with get_db() as db:
        return (
            db.query(Repuesto)
            .filter(Repuesto.stock < limite)
            .order_by(Repuesto.stock)
            .all()
        )


# =====================================
# CONSULTAS PARA DASHBOARD
# =====================================

@st.cache_data(ttl=60)
def sumar_duracion_total():
    with get_db() as db:
        return db.query(func.coalesce(func.sum(EventoMantenimiento.duracion_minutos), 0)).scalar()


@st.cache_data(ttl=60)
def sumar_duracion_mes():
    inicio_mes = datetime.now().replace(
        day=1, hour=0, minute=0, second=0, microsecond=0
    )
    with get_db() as db:
        return db.query(func.coalesce(func.sum(EventoMantenimiento.duracion_minutos), 0)).filter(
            EventoMantenimiento.fecha >= inicio_mes
        ).scalar()

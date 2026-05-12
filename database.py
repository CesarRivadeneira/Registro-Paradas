import hashlib
import json
import os
import base64
import time
from contextlib import contextmanager
from datetime import datetime

import streamlit as st
from sqlalchemy import create_engine, text, func
from sqlalchemy.orm import sessionmaker, joinedload
from sqlalchemy.exc import SQLAlchemyError, OperationalError

try:
    from config import DATABASE_URL
except Exception:
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///mantenimiento.db")

from models import Base, Sector, Linea, Equipo, Repuesto, Usuario, EventoMantenimiento, SolicitudReparacion

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
        except SQLAlchemyError:
            # Tablas/sequences ya existen (ej. PostgreSQL reintenta crear sequences existentes)
            _migrar_base()
            return


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
            ("usuarios", "permisos_extra", "TEXT"),
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
        "CREATE INDEX IF NOT EXISTS ix_solicitudes_linea_id ON solicitudes_reparacion(linea_id)",
        "CREATE INDEX IF NOT EXISTS ix_solicitudes_fecha ON solicitudes_reparacion(fecha_solicitud)",
    ]
    for idx in indices:
        try:
            db.execute(text(idx))
            db.commit()
        except Exception:
            pass


def _migracion_ya_aplicada(db, dialect):
    """Retorna True si permisos_extra ya existe (migración completa)."""
    try:
        if dialect == "postgresql":
            result = db.execute(
                text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_name='usuarios' AND column_name='permisos_extra'"
                )
            ).fetchone()
            return result is not None
        elif dialect == "sqlite":
            conn = db.connection().connection
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(usuarios)")
            cols = {row[1] for row in cursor.fetchall()}
            return "permisos_extra" in cols
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


def guardar_permisos_extras(usuario_id, permisos_dict):
    with get_db() as db:
        user = db.query(Usuario).get(usuario_id)
        if user:
            user.permisos_extra = json.dumps(permisos_dict) if permisos_dict else None
            db.commit()
    st.cache_data.clear()


# =====================================
# CRUD EVENTOS
# =====================================

def editar_evento(evento_id, fecha, hora_inicio, duracion_minutos, falla, accion, repuesto_id):
    with get_db() as db:
        evento = db.query(EventoMantenimiento).get(evento_id)
        if evento:
            evento.fecha = fecha
            evento.hora_inicio = hora_inicio
            evento.duracion_minutos = duracion_minutos
            evento.falla = falla
            evento.accion = accion
            evento.repuesto_id = repuesto_id
            db.commit()
    st.cache_data.clear()


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


def obtener_eventos_por_usuario(user_id):
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
            .filter(EventoMantenimiento.user_id == user_id)
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


# =====================================
# MTTR / MTBF
# =====================================


def _dias_en_periodo(desde, hasta, modo):
    """Retorna cantidad de días operativos en el período."""
    if modo == "24/7":
        return (hasta - desde).days
    dias = 0
    delta = hasta - desde
    for i in range(delta.days):
        dia = desde + __import__("datetime").timedelta(days=i)
        if dia.weekday() < 5:
            dias += 1
    return max(dias, 1)


@st.cache_data(ttl=60)
def calcular_mttr_global(desde, hasta):
    """MTTR global en horas para el período."""
    with get_db() as db:
        row = db.query(
            func.coalesce(func.sum(EventoMantenimiento.duracion_minutos), 0),
            func.count(EventoMantenimiento.id),
        ).filter(
            EventoMantenimiento.fecha >= desde,
            EventoMantenimiento.fecha <= hasta,
        ).first()
        total_min, count = row
    if count == 0:
        return 0.0
    return round(total_min / count / 60, 2)


@st.cache_data(ttl=60)
def calcular_mtbf_global(desde, hasta, modo):
    """MTBF global en horas para el período."""
    with get_db() as db:
        row = db.query(
            func.coalesce(func.sum(EventoMantenimiento.duracion_minutos), 0),
            func.count(EventoMantenimiento.id),
        ).filter(
            EventoMantenimiento.fecha >= desde,
            EventoMantenimiento.fecha <= hasta,
        ).first()
        total_min, count = row
    if count == 0:
        return 0.0
    op_horas = _dias_en_periodo(desde, hasta, modo) * 24
    downtime_horas = total_min / 60
    return round((op_horas - downtime_horas) / count, 2)


@st.cache_data(ttl=60)
def calcular_kpi_por_linea(desde, hasta, modo):
    """DataFrame con fallas, downtime, MTTR y MTBF por línea."""
    import pandas as pd

    with get_db() as db:
        rows = (
            db.query(
                Sector.nombre.label("sector"),
                Linea.nombre.label("linea"),
                func.count(EventoMantenimiento.id).label("fallas"),
                func.coalesce(func.sum(EventoMantenimiento.duracion_minutos), 0).label("downtime_min"),
            )
            .select_from(EventoMantenimiento)
            .join(Equipo, EventoMantenimiento.equipo_id == Equipo.id)
            .join(Linea, Equipo.linea_id == Linea.id)
            .join(Sector, Linea.sector_id == Sector.id)
            .filter(
                EventoMantenimiento.fecha >= desde,
                EventoMantenimiento.fecha <= hasta,
            )
            .group_by(Sector.id, Linea.id)
            .all()
        )

    df = pd.DataFrame(rows, columns=["sector", "linea", "fallas", "downtime_min"])
    if df.empty:
        return df
    op_horas = _dias_en_periodo(desde, hasta, modo) * 24
    df["mttr_h"] = (df["downtime_min"] / df["fallas"] / 60).round(2)
    df["mtbf_h"] = ((op_horas - df["downtime_min"] / 60) / df["fallas"]).round(2)
    return df.sort_values("fallas", ascending=False).reset_index(drop=True)


@st.cache_data(ttl=300)
def calcular_evolucion_mensual(modo, meses=12):
    """DataFrame con MTTR y MTBF mes a mes."""
    import pandas as pd

    hoy = datetime.now()
    mes_inicio = hoy.month - (meses - 1)
    año_inicio = hoy.year
    while mes_inicio < 1:
        mes_inicio += 12
        año_inicio -= 1
    desde = hoy.replace(year=año_inicio, month=mes_inicio, day=1)

    with get_db() as db:
        dialect = db.bind.dialect.name
        if dialect == "postgresql":
            month_expr = func.DATE_TRUNC("month", EventoMantenimiento.fecha).label("mes")
        else:
            month_expr = func.strftime("%Y-%m-01", EventoMantenimiento.fecha).label("mes")

        rows = (
            db.query(
                month_expr,
                func.count(EventoMantenimiento.id).label("fallas"),
                func.coalesce(func.sum(EventoMantenimiento.duracion_minutos), 0).label("downtime_min"),
            )
            .filter(EventoMantenimiento.fecha >= desde)
            .group_by("mes")
            .order_by("mes")
            .all()
        )

    data = []
    for r in rows:
        mes, fallas, downtime = r
        if fallas == 0:
            continue
        mttr = round(downtime / fallas / 60, 2)
        # Estimar MTBF asumiendo 30 días por mes
        dias_op = 30 if modo == "24/7" else 22
        op_horas = dias_op * 24
        mtbf = round((op_horas - downtime / 60) / fallas, 2)
        data.append({"mes": mes, "mttr_h": mttr, "mtbf_h": mtbf})

    return pd.DataFrame(data).sort_values("mes")


# =====================================
# CRUD SOLICITUDES DE REPARACIÓN
# =====================================


def crear_solicitud(linea_id, descripcion, solicitante_id, equipo_id=None):
    with get_db() as db:
        solicitud = SolicitudReparacion(
            linea_id=linea_id,
            equipo_id=equipo_id,
            descripcion=descripcion,
            solicitante_id=solicitante_id,
        )
        db.add(solicitud)
        db.commit()
    st.cache_data.clear()


def obtener_solicitudes():
    with get_db() as db:
        return (
            db.query(SolicitudReparacion)
            .options(
                joinedload(SolicitudReparacion.linea).joinedload(Linea.sector),
                joinedload(SolicitudReparacion.equipo),
                joinedload(SolicitudReparacion.solicitante),
                joinedload(SolicitudReparacion.programado_por),
                joinedload(SolicitudReparacion.ejecutado_por),
            )
            .order_by(SolicitudReparacion.fecha_solicitud.desc())
            .all()
        )


def programar_solicitud(solicitud_id, fecha_programada, usuario_id):
    with get_db() as db:
        sol = db.query(SolicitudReparacion).get(solicitud_id)
        if sol and sol.estado == "pendiente":
            sol.estado = "programada"
            sol.fecha_programada = fecha_programada
            sol.programado_por_id = usuario_id
            db.commit()
    st.cache_data.clear()


def completar_solicitud(solicitud_id, usuario_id, observaciones=""):
    with get_db() as db:
        sol = db.query(SolicitudReparacion).get(solicitud_id)
        if sol and sol.estado == "programada":
            sol.estado = "realizada"
            sol.fecha_ejecucion = datetime.now()
            sol.ejecutado_por_id = usuario_id
            sol.observaciones = observaciones or None
            db.commit()
    st.cache_data.clear()


def rechazar_solicitud(solicitud_id, usuario_id, motivo):
    with get_db() as db:
        sol = db.query(SolicitudReparacion).get(solicitud_id)
        if sol and sol.estado == "pendiente":
            sol.estado = "rechazada"
            sol.ejecutado_por_id = usuario_id
            sol.fecha_ejecucion = datetime.now()
            sol.motivo_rechazo = motivo
            db.commit()
    st.cache_data.clear()

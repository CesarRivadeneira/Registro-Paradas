from datetime import datetime

from sqlalchemy import (
    Table, Column, Integer, String, DateTime, Text, ForeignKey, Boolean
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

evento_repuestos = Table(
    "evento_repuestos",
    Base.metadata,
    Column("evento_id", Integer, ForeignKey("eventos.id"), primary_key=True),
    Column("repuesto_id", Integer, ForeignKey("repuestos.id"), primary_key=True),
)

reparacion_repuestos = Table(
    "reparacion_repuestos",
    Base.metadata,
    Column("reparacion_id", Integer, ForeignKey("reparaciones.id"), primary_key=True),
    Column("repuesto_id", Integer, ForeignKey("repuestos.id"), primary_key=True),
)


class Sector(Base):
    __tablename__ = "sectores"
    id = Column(Integer, primary_key=True)
    nombre = Column(String, unique=True, nullable=False)
    lineas = relationship("Linea", back_populates="sector")


class Linea(Base):
    __tablename__ = "lineas"
    id = Column(Integer, primary_key=True)
    nombre = Column(String, nullable=False)
    sector_id = Column(Integer, ForeignKey("sectores.id"), index=True)
    sector = relationship("Sector", back_populates="lineas")
    equipos = relationship("Equipo", back_populates="linea")


class Equipo(Base):
    __tablename__ = "equipos"
    id = Column(Integer, primary_key=True)
    nombre = Column(String, nullable=False)
    tipo = Column(String, nullable=False)
    linea_id = Column(Integer, ForeignKey("lineas.id"))
    linea = relationship("Linea", back_populates="equipos")


class Repuesto(Base):
    __tablename__ = "repuestos"
    id = Column(Integer, primary_key=True)
    nombre = Column(String, nullable=False)
    codigo = Column(String, unique=True)
    stock = Column(Integer, default=0)


class Usuario(Base):
    __tablename__ = "usuarios"
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    nombre_completo = Column(String, default="")
    rol = Column(String, default="tecnico")
    activo = Column(Boolean, default=True)
    permisos_extra = Column(Text, nullable=True)


class EventoMantenimiento(Base):
    __tablename__ = "eventos"
    id = Column(Integer, primary_key=True)
    fecha = Column(DateTime, default=datetime.now, index=True)
    hora_inicio = Column(String, default="")
    duracion_minutos = Column(Integer, default=0)
    equipo_id = Column(Integer, ForeignKey("equipos.id"), index=True)
    falla = Column(Text)
    accion = Column(Text)
    repuesto_id = Column(Integer, ForeignKey("repuestos.id"))
    tecnico = Column(String)
    observaciones = Column(Text)
    user_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    equipo = relationship("Equipo")
    repuesto = relationship("Repuesto")
    repuestos = relationship("Repuesto", secondary=evento_repuestos)
    usuario = relationship("Usuario")


class SolicitudReparacion(Base):
    __tablename__ = "solicitudes_reparacion"
    id = Column(Integer, primary_key=True)
    fecha_solicitud = Column(DateTime, default=datetime.now, index=True)
    linea_id = Column(Integer, ForeignKey("lineas.id"), nullable=False, index=True)
    equipo_id = Column(Integer, ForeignKey("equipos.id"), nullable=True)
    descripcion = Column(Text, nullable=False)
    solicitante_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    estado = Column(String, default="pendiente")
    fecha_programada = Column(DateTime, nullable=True)
    programado_por_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    fecha_ejecucion = Column(DateTime, nullable=True)
    ejecutado_por_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    observaciones = Column(Text, nullable=True)
    motivo_rechazo = Column(Text, nullable=True)

    linea = relationship("Linea", backref="solicitudes")
    equipo = relationship("Equipo", backref="solicitudes")
    solicitante = relationship("Usuario", foreign_keys=[solicitante_id], backref="solicitudes_creadas")
    programado_por = relationship("Usuario", foreign_keys=[programado_por_id], backref="solicitudes_programadas")
    ejecutado_por = relationship("Usuario", foreign_keys=[ejecutado_por_id], backref="solicitudes_ejecutadas")


class Reparacion(Base):
    __tablename__ = "reparaciones"
    id = Column(Integer, primary_key=True)
    fecha = Column(DateTime, default=datetime.now, index=True)
    equipo_id = Column(Integer, ForeignKey("equipos.id"), nullable=True, index=True)
    trabajo = Column(Text, nullable=False)
    user_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    observaciones = Column(Text, nullable=True)
    solicitud_id = Column(Integer, ForeignKey("solicitudes_reparacion.id"), nullable=True, index=True)

    equipo = relationship("Equipo")
    usuario = relationship("Usuario")
    solicitud = relationship("SolicitudReparacion")
    repuestos = relationship("Repuesto", secondary=reparacion_repuestos)

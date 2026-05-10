from datetime import datetime

from sqlalchemy import (
    Column, Integer, String, DateTime, Text, ForeignKey, Boolean
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Sector(Base):
    __tablename__ = "sectores"
    id = Column(Integer, primary_key=True)
    nombre = Column(String, unique=True, nullable=False)
    lineas = relationship("Linea", back_populates="sector")


class Linea(Base):
    __tablename__ = "lineas"
    id = Column(Integer, primary_key=True)
    nombre = Column(String, nullable=False)
    sector_id = Column(Integer, ForeignKey("sectores.id"))
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


class EventoMantenimiento(Base):
    __tablename__ = "eventos"
    id = Column(Integer, primary_key=True)
    fecha = Column(DateTime, default=datetime.now)
    hora_inicio = Column(String, default="")
    duracion_minutos = Column(Integer, default=0)
    equipo_id = Column(Integer, ForeignKey("equipos.id"))
    falla = Column(Text)
    accion = Column(Text)
    repuesto_id = Column(Integer, ForeignKey("repuestos.id"))
    tecnico = Column(String)
    observaciones = Column(Text)
    user_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    equipo = relationship("Equipo")
    repuesto = relationship("Repuesto")
    usuario = relationship("Usuario")

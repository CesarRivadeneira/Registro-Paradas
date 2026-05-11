# Sistema de Gestión de Mantenimiento — Registro de Paradas

Aplicación web interna para registrar y dar seguimiento a paradas de línea/equipo en una planta fabril. Permite visualizar KPIs por sector, línea y equipo, gestionar usuarios por roles, y mantener un historial completo de eventos de mantenimiento.

## Funcionalidades

- **Registro de paradas** — Selección jerárquica Sector → Línea → Equipo, con duración, descripción de falla, acción correctiva y repuesto utilizado.
- **Dashboard** — Panel de control con métricas (total paradas, paradas del mes, downtime acumulado) y gráficos verticales por sector, línea y equipo. Filtros dinámicos por sector/línea/equipo.
- **Historial** — Vista completa de todas las paradas con filtros por rango de fechas y equipo. Exportación a Excel (solo admin).
- **Gestión de maestros** — ABM de sectores, líneas, equipos, repuestos y usuarios.
- **Roles de usuario:**
  - **Admin** — Acceso completo a todas las funcionalidades incluyendo gestión de usuarios y exportación.
  - **Técnico** — Visualización de sectores/líneas/equipos, registro de paradas, historial (sin exportar).
  - **Operario** — Registro de paradas y acceso al historial.
  - **Producción** — Solo dashboard e historial (solo lectura).

- **Autenticación** — Credenciales generadas automáticamente: usuario = primera letra del nombre + primeras 3 letras del apellido + DNI; contraseña = primera letra del apellido + DNI.

## Stack tecnológico

| Componente | Tecnología |
|---|---|
| Frontend / Backend | Python + [Streamlit](https://streamlit.io) |
| ORM | SQLAlchemy |
| Base de datos | PostgreSQL ([Neon](https://neon.tech)) en producción, SQLite en desarrollo local |
| Gráficos | Altair |
| Despliegue | [Streamlit Cloud](https://share.streamlit.io) |

## Desarrollo local

1. Clonar el repositorio:
   ```bash
   git clone https://github.com/CesarRivadeneira/Registro-Paradas.git
   cd Registro-Paradas
   ```

2. Crear y activar un entorno virtual:
   ```bash
   python -m venv venv
   .\venv\Scripts\activate  # Windows
   source venv/bin/activate  # Linux/Mac
   ```

3. Instalar dependencias:
   ```bash
   pip install -r requirements.txt
   ```

4. Crear archivo `.env` en la raíz con:
   ```env
   DATABASE_URL=sqlite:///mantenimiento_v3.db
   ```

5. Ejecutar la app:
   ```bash
   streamlit run app.py
   ```

## Despliegue en Streamlit Cloud

1. Conectar el repositorio (puede ser privado) en [share.streamlit.io](https://share.streamlit.io).
2. Configurar el archivo principal como `app.py`.
3. En **Settings → Secrets**, agregar la URL de conexión a PostgreSQL:
   ```toml
   DATABASE_URL = "postgresql://usuario:password@host.com/basedatos?sslmode=require"
   ```

> **Importante:** Streamlit Cloud usa almacenamiento efímero. Los datos en SQLite se pierden al redeployar. Siempre usar PostgreSQL en producción.

## Licencia

Uso interno — Planta fabril.

# Sistema de Gestión de Mantenimiento — Registro de Paradas

Aplicación web para registro y seguimiento de paradas de línea/equipo en planta fabril.
KPIs MTTR/MTBF por sector/línea/equipo, solicitudes de reparación, roles con permisos
granulares. Multi‑usuario, desplegada en Streamlit Cloud + Neon PostgreSQL.

## Funcionalidades

- **Registro de paradas** — Selección jerárquica Sector → Línea → Equipo con hora de
  inicio, duración, falla, acción correctiva y repuesto.
- **Editar paradas** — Técnico/operario editan sus propias paradas; admin/supervisor
  editan cualquier parada desde la misma pantalla de registro.
- **Dashboard MTTR/MTBF** — Tarjetas de métricas globales, top 10 peores MTTR/MTBF por
  línea, evolución mensual, tabla de KPIs por línea, filtros por período y modo operativo
  (24/7 o 24/5).
- **Historial** — Listado completo con filtros por fecha y equipo, exportación a Excel.
- **Solicitudes de Reparación** — Workflow `pendiente → programada → realizada` /
  `rechazada` (con motivo obligatorio). Creación: admin/supervisor/técnico/operario.
  Gestión: admin/supervisor.
- **Gestión de maestros** — ABM de sectores, líneas, equipos, repuestos y usuarios.
- **Roles de usuario:**
  - **Admin** — Acceso completo + gestión de usuarios y permisos.
  - **Supervisor** — CRUD de paradas, gestiona solicitudes, edita cualquier parada.
  - **Técnico** — Registra paradas, edita las propias, crea solicitudes.
  - **Operario** — Registra paradas propias, edita las propias, crea solicitudes.
  - **Producción** — Solo lectura: historial y solicitudes (sin crear).
- **Permisos granulares** — Cada rol tiene permisos default extensibles vía
  `permisos_extra` por usuario desde el panel de administración.
- **Autenticación** — PBKDF2 con hash + sal. Credenciales auto‑generadas:
  usuario = `1er letra nombre + 3 primeras apellido + DNI`,
  contraseña = `1er letra apellido + DNI`.
- **Modo operativo configurable** — 24/7 (todos los días) o 24/5 (solo lunes a viernes)
  para cálculo de MTBF.

## Stack tecnológico

| Componente | Tecnología |
|---|---|
| Frontend / Backend | Python + [Streamlit](https://streamlit.io) 1.57 |
| ORM | SQLAlchemy 2.0 + PostgreSQL / SQLite |
| Base de datos | [Neon PostgreSQL](https://neon.tech) (producción), SQLite (local) |
| Gráficos | Altair 6.1 |
| Autenticación | PBKDF2 (hashlib) |
| Despliegue | [Streamlit Cloud](https://share.streamlit.io) |

## Desarrollo local

1. Clonar:
   ```bash
   git clone https://github.com/CesarRivadeneira/Registro-Paradas.git
   cd Registro-Paradas
   ```

2. Entorno virtual:
   ```bash
   python -m venv venv
   .\venv\Scripts\activate   # Windows
   source venv/bin/activate  # Linux/Mac
   ```

3. Dependencias:
   ```bash
   pip install -r requirements.txt
   ```

4. Crear `.env`:
   ```env
   DATABASE_URL=sqlite:///mantenimiento.db
   ```

5. Ejecutar:
   ```bash
   streamlit run app.py
   ```

## Despliegue en Streamlit Cloud

1. Conectar el repositorio en [share.streamlit.io](https://share.streamlit.io).
2. Archivo principal: `app.py`.
3. En **Settings → Secrets**, agregar:
   ```toml
   DATABASE_URL = "postgresql://usuario:password@host.neon.tech/basedatos?sslmode=require"
   ```

> SQLite en Streamlit Cloud es efímero — los datos se pierden al redeployar.
> Siempre usar PostgreSQL en producción.

## Licencia

Uso interno — Planta fabril.

import streamlit as st
import pandas as pd
import altair as alt
from io import BytesIO
from datetime import datetime, date

from database import (
    init_db,
    crear_sector,
    obtener_sectores,
    eliminar_sector,
    crear_linea,
    obtener_lineas,
    obtener_lineas_por_sector,
    eliminar_linea,
    crear_equipo,
    obtener_equipos,
    obtener_equipos_por_linea,
    eliminar_equipo,
    crear_repuesto,
    obtener_repuestos,
    crear_evento,
    obtener_eventos,
    obtener_eventos_recientes,
    contar_eventos_mes,
    contar_eventos_por_equipo,
    contar_eventos_por_sector,
    repuestos_bajo_stock,
    sumar_duracion_total,
    sumar_duracion_mes,
    obtener_resumen_dashboard,
    crear_usuario,
    autenticar,
    hay_usuarios,
    obtener_usuarios,
    desactivar_usuario,
)

DURACION_OPTS = {
    "5 min": 5, "10 min": 10, "15 min": 15, "20 min": 20,
    "30 min": 30, "45 min": 45,
    "1 hora": 60, "1h 30m": 90,
    "2 horas": 120, "2h 30m": 150,
    "3 horas": 180, "3h 30m": 210,
    "4 horas": 240, "Más de 4h": 999,
}


def fmt_duracion(minutos):
    if minutos >= 60:
        h = minutos // 60
        m = minutos % 60
        return f"{h}h {m}m" if m else f"{h}h"
    return f"{minutos} min"

# =====================================
# CONFIG STREAMLIT
# =====================================

st.set_page_config(page_title="Gestión de Mantenimiento", layout="wide")

st.markdown(
    """
<style>
header[data-testid="stHeader"] { display: none; }
</style>
""",
    unsafe_allow_html=True,
)

# =====================================
# INICIALIZAR DB
# =====================================

try:
    init_db()
except Exception as e:
    st.error(f"Error de conexión a la base de datos: {e}")
    st.info("Verificá que el secret DATABASE_URL esté configurado correctamente en Streamlit Cloud.")
    st.stop()

# =====================================
# CARGA INICIAL (solo si vacío)
# =====================================

sectores_default = [
    "Cosmetica 1",
    "Cosmetica 2",
    "Paletizado",
    "Despaletizado",
    "Envasado",
    "Depósito",
]

lineas_default = {
    "Cosmetica 1": ["Odorono", "Línea 5"],
    "Cosmetica 2": ["Línea 1", "Línea 2"],
    "Paletizado": ["Paletizado 1"],
    "Despaletizado": ["Despaletizado 1"],
    "Envasado": ["Envasado 1", "Envasado 2"],
}

if len(obtener_sectores()) == 0:
    for s in sectores_default:
        crear_sector(s)
    for sec_nombre, lineas in lineas_default.items():
        sector = next((s for s in obtener_sectores() if s.nombre == sec_nombre), None)
        if sector:
            for linea_nombre in lineas:
                crear_linea(linea_nombre, sector.id)

# =====================================
# LOGIN
# =====================================

if "user" not in st.session_state:
    st.session_state.user = None

if not st.session_state.user:
    st.title("Sistema de Gestión de Mantenimiento")

    if not hay_usuarios():
        st.subheader("Crear primer usuario (administrador)")

        if "creds" not in st.session_state:
            st.session_state.creds = None

        with st.form("crear_admin"):
            nombre = st.text_input("Nombre")
            apellido = st.text_input("Apellido")
            dni = st.text_input("DNI")

            if st.form_submit_button("Generar credenciales"):
                if nombre and apellido and dni:
                    u = (nombre[0] + apellido[:3]).lower()
                    p = (apellido[0] + dni).lower()
                    nc = f"{nombre} {apellido}"
                    st.session_state.creds = (u, p, nc)

        if st.session_state.creds:
            u, p, nc = st.session_state.creds
            st.info(f"**Usuario:** `{u}`  \n**Contraseña:** `{p}`")
            if st.button("Confirmar y crear administrador"):
                ok, msg = crear_usuario(u, p, nc, rol="admin")
                if ok:
                    st.success("Administrador creado. Inicie sesión.")
                    st.session_state.creds = None
                    st.rerun()
                else:
                    st.warning(msg)
                    st.session_state.creds = None
    else:
        st.subheader("Iniciar sesión")
        with st.form("login"):
            u = st.text_input("Usuario")
            p = st.text_input("Contraseña", type="password")
            if st.form_submit_button("Ingresar"):
                user = autenticar(u, p)
                if user:
                    st.session_state.user = user
                    st.rerun()
                else:
                    st.error("Usuario o contraseña incorrectos")
    st.stop()

# =====================================
# USUARIO LOGUEADO
# =====================================

user = st.session_state.user
rol = user.rol

st.sidebar.markdown(
    f"🔧 **Bienvenido, {user.nombre_completo or user.username}**"
)
st.sidebar.markdown(f"**Rol:** {rol}")
st.sidebar.markdown("---")

# =====================================
# PAGE FUNCTIONS
# =====================================

def page_inicio():
    st.title("Sistema de Gestión de Mantenimiento")
    st.header("Panel de Control")

    col_b1, col_b2, col_b3, col_b4 = st.columns([2, 1, 1, 1])
    with col_b1:
        if st.button("➕ Registrar Parada", use_container_width=True, type="primary"):
            if _pg_paradas:
                st.switch_page(_pg_paradas)
    with col_b2:
        st.metric("Total Paradas", len(obtener_eventos()))
    with col_b3:
        st.metric("Este mes", contar_eventos_mes())
    with col_b4:
        st.metric("Downtime total", fmt_duracion(sumar_duracion_total()))

    st.markdown("---")

    dashboard_section()


def page_sectores():
    st.header("Sectores")

    if rol == "admin":
        col_s1, col_s2 = st.columns([2, 1])
        with col_s1:
            nuevo_sector = st.text_input("Nuevo sector", label_visibility="collapsed", placeholder="Nombre del nuevo sector")
        with col_s2:
            if st.button("Guardar sector", use_container_width=True):
                crear_sector(nuevo_sector)
                st.success("Sector guardado")
        st.markdown("---")

    sectores = obtener_sectores()
    df = pd.DataFrame(
        [{"ID": s.id, "Sector": s.nombre} for s in sectores]
    )
    st.dataframe(df, width="stretch")

    if rol == "admin" and sectores:
        with st.expander("Eliminar sector"):
            sector_a_borrar = st.selectbox(
                "Seleccionar sector a eliminar",
                sectores,
                format_func=lambda x: x.nombre,
                key="del_sector",
            )
            if st.button("Eliminar sector", type="primary"):
                eliminar_sector(sector_a_borrar.id)
                st.success(f"Sector '{sector_a_borrar.nombre}' y sus líneas eliminados")
                st.rerun()


def page_lineas():
    st.header("Líneas de Producción")

    if rol == "admin":
        sectores = obtener_sectores()
        col_l1, col_l2 = st.columns(2)
        with col_l1:
            sector_nuevo = st.selectbox(
                "Sector", sectores, format_func=lambda x: x.nombre, key="sel_sector_linea"
            )
        with col_l2:
            nombre_linea = st.text_input("Nombre de la línea")

        if st.button("Guardar línea"):
            crear_linea(nombre_linea, sector_nuevo.id)
            st.success("Línea guardada")
        st.markdown("---")

    lineas = obtener_lineas()
    df = pd.DataFrame(
        [
            {"ID": l.id, "Línea": l.nombre, "Sector": l.sector.nombre}
            for l in lineas
        ]
    )
    st.dataframe(df, width="stretch")

    if rol == "admin" and lineas:
        with st.expander("Eliminar línea"):
            linea_a_borrar = st.selectbox(
                "Seleccionar línea a eliminar",
                lineas,
                format_func=lambda x: f"{x.nombre} ({x.sector.nombre})",
                key="del_linea",
            )
            if st.button("Eliminar línea", type="primary"):
                eliminar_linea(linea_a_borrar.id)
                st.success(f"Línea '{linea_a_borrar.nombre}' y sus equipos eliminados")
                st.rerun()


def page_equipos():
    st.header("Equipos / Robots")

    if rol == "admin":
        sectores = obtener_sectores()
        nombre = st.text_input("Nombre del equipo")
        tipo = st.selectbox("Tipo", ["Robot", "Cobot", "Máquina", "PLC", "Otro"])

        sector_sel = st.selectbox(
            "Sector", sectores, format_func=lambda x: x.nombre, key="sector_equipo"
        )
        lineas_del_sector = obtener_lineas_por_sector(sector_sel.id)

        if not lineas_del_sector:
            st.warning("Primero debe crear líneas para este sector en el menú Líneas")
            st.stop()

        linea_sel = st.selectbox(
            "Línea", lineas_del_sector, format_func=lambda x: x.nombre
        )

        if st.button("Guardar equipo"):
            crear_equipo(nombre, tipo, linea_sel.id)
            st.success("Equipo registrado")
        st.markdown("---")

    equipos = obtener_equipos()

    df = pd.DataFrame(
        [
            {
                "ID": e.id,
                "Nombre": e.nombre,
                "Tipo": e.tipo,
                "Línea": e.linea.nombre if e.linea else "",
                "Sector": e.linea.sector.nombre if e.linea and e.linea.sector else "",
            }
            for e in equipos
        ]
    )
    st.dataframe(df, width="stretch")

    if rol == "admin" and equipos:
        with st.expander("Eliminar equipo"):
            equipo_a_borrar = st.selectbox(
                "Seleccionar equipo a eliminar",
                equipos,
                format_func=lambda x: f"{x.nombre} - {x.linea.nombre if x.linea else ''}",
                key="del_equipo",
            )
            if st.button("Eliminar equipo", type="primary"):
                eliminar_equipo(equipo_a_borrar.id)
                st.success(f"Equipo '{equipo_a_borrar.nombre}' eliminado")
                st.rerun()


def page_repuestos():
    st.header("Gestión de Repuestos")

    nombre = st.text_input("Nombre repuesto")
    codigo = st.text_input("Código")
    stock = st.number_input("Stock", min_value=0)

    if st.button("Guardar repuesto"):
        ok, mensaje = crear_repuesto(nombre, codigo, stock)
        if ok:
            st.success(mensaje)
        else:
            st.warning(mensaje)

    repuestos = obtener_repuestos()

    df = pd.DataFrame(
        [
            {"ID": r.id, "Nombre": r.nombre, "Código": r.codigo, "Stock": r.stock}
            for r in repuestos
        ]
    )

    st.dataframe(df, width="stretch")


def page_paradas():
    st.header("Registrar Parada de Línea / Equipo")

    sectores = obtener_sectores()
    repuestos = obtener_repuestos()
    tecnico_nombre = user.nombre_completo or user.username

    if len(sectores) == 0:
        st.warning("Primero debe haber sectores registrados")
        st.stop()

    sector_sel = st.selectbox(
        "Sector", sectores, format_func=lambda x: x.nombre, key="ev_sector"
    )
    lineas_del_sector = obtener_lineas_por_sector(sector_sel.id)

    if not lineas_del_sector:
        st.warning("No hay líneas en este sector")
        st.stop()

    linea_sel = st.selectbox(
        "Línea", lineas_del_sector, format_func=lambda x: x.nombre, key="ev_linea"
    )
    equipos_de_linea = obtener_equipos_por_linea(linea_sel.id)

    if not equipos_de_linea:
        st.warning("No hay equipos registrados en esta línea")
        st.stop()

    equipo = st.selectbox(
        "Equipo", equipos_de_linea, format_func=lambda x: x.nombre, key="ev_equipo"
    )

    col_t1, col_t2 = st.columns(2)
    with col_t1:
        fecha_parada = st.date_input("Fecha de la parada", value=date.today())
        hora_inicio = st.time_input("Hora de inicio de la parada", value=None, step=900)
    with col_t2:
        duracion_label = st.selectbox(
            "Duración de la parada",
            list(DURACION_OPTS.keys()),
            index=4,
        )
        duracion_val = DURACION_OPTS[duracion_label]

    falla = st.text_area("Descripción de la falla / motivo de la parada")
    accion = st.text_area("Acción realizada para la resolución")

    repuesto_opciones = [None] + repuestos
    repuesto = st.selectbox(
        "Repuesto utilizado",
        repuesto_opciones,
        format_func=lambda x: "Ninguno" if x is None else f"{x.nombre} (stock: {x.stock})",
    )

    st.caption(f"Técnico responsable: {tecnico_nombre}")

    if st.button("Guardar parada"):
        errores = []
        if not falla.strip():
            errores.append("La descripción de la falla / motivo es obligatorio")
        if not accion.strip():
            errores.append("Debe indicar la acción realizada para la resolución")
        if not hora_inicio:
            errores.append("Debe indicar la hora de inicio de la parada")
        if duracion_val == 0:
            errores.append("Debe seleccionar una duración válida")

        if errores:
            for e in errores:
                st.error(e)
        else:
            hora_str = hora_inicio.strftime("%H:%M")
            crear_evento(
                equipo.id,
                falla.strip(),
                accion.strip(),
                repuesto.id if repuesto else None,
                tecnico_nombre,
                "",
                user_id=user.id,
                hora_inicio=hora_str,
                duracion_minutos=duracion_val,
            )
            st.success("Parada registrada correctamente")


def page_historial():
    st.header("Historial de Paradas")

    eventos = obtener_eventos()

    df = pd.DataFrame(
        [
            {
                "Fecha": e.fecha,
                "Hora inicio": e.hora_inicio,
                "Duración": fmt_duracion(e.duracion_minutos) if e.duracion_minutos else "",
                "Equipo": e.equipo.nombre,
                "Línea": e.equipo.linea.nombre if e.equipo and e.equipo.linea else "",
                "Sector": e.equipo.linea.sector.nombre if e.equipo and e.equipo.linea and e.equipo.linea.sector else "",
                "Falla": e.falla,
                "Acción": e.accion,
                "Repuesto": e.repuesto.nombre if e.repuesto else "",
                "Técnico": e.tecnico,
                "Registró": e.usuario.nombre_completo or e.usuario.username if e.usuario else "",
                "Observaciones": e.observaciones,
            }
            for e in eventos
        ]
    )

    with st.expander("Filtros", expanded=True):
        col_f1, col_f2, col_f3 = st.columns(3)
        with col_f1:
            fecha_desde = st.date_input("Desde", value=None)
        with col_f2:
            fecha_hasta = st.date_input("Hasta", value=None)
        with col_f3:
            nombres_equipos = sorted(df["Equipo"].unique()) if not df.empty else []
            equipos_filtro = st.multiselect("Equipo", nombres_equipos)

    df_filtrado = df.copy()
    if fecha_desde:
        df_filtrado = df_filtrado[
            pd.to_datetime(df_filtrado["Fecha"]).dt.date >= fecha_desde
        ]
    if fecha_hasta:
        df_filtrado = df_filtrado[
            pd.to_datetime(df_filtrado["Fecha"]).dt.date <= fecha_hasta
        ]
    if equipos_filtro:
        df_filtrado = df_filtrado[df_filtrado["Equipo"].isin(equipos_filtro)]

    st.markdown(f"**{len(df_filtrado)} paradas encontradas**")
    st.dataframe(df_filtrado, width="stretch")

    if not df_filtrado.empty and rol == "admin":
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            df_filtrado.to_excel(writer, index=False, sheet_name="Paradas")
        st.download_button(
            label="Exportar a Excel",
            data=buffer.getvalue(),
            file_name=f"paradas_mantenimiento_{date.today()}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )


def page_usuarios():
    st.header("Gestión de Usuarios")

    with st.expander("Registrar nuevo usuario", expanded=True):
        col_u1, col_u2 = st.columns(2)
        with col_u1:
            u_nombre = st.text_input("Nombre", key="u_nombre")
            u_dni = st.text_input("DNI", key="u_dni")
        with col_u2:
            u_apellido = st.text_input("Apellido", key="u_apellido")
            u_rol = st.selectbox(
                "Rol",
                ["tecnico", "operario", "produccion"],
                key="u_rol",
            )

        if st.button("Generar y guardar usuario"):
            if u_nombre and u_apellido and u_dni:
                u_username = (u_nombre[0] + u_apellido[:3]).lower()
                u_password = (u_apellido[0] + u_dni).lower()
                u_nc = f"{u_nombre} {u_apellido}"
                ok, msg = crear_usuario(u_username, u_password, u_nc, rol=u_rol)
                if ok:
                    st.success(
                        f"Usuario **{u_username}** creado con rol **{u_rol}**"
                    )
                    st.info(f"**Usuario:** `{u_username}`  \n**Contraseña:** `{u_password}`")
                else:
                    st.warning(msg)

    st.markdown("---")
    st.subheader("Usuarios registrados")

    usuarios = obtener_usuarios()
    if usuarios:
        for usr in usuarios:
            col_a, col_b, col_c, col_d, col_e = st.columns([2, 2, 1, 1, 1])
            col_a.write(usr.nombre_completo or usr.username)
            col_b.write(usr.username)
            col_c.write(usr.rol)
            col_d.write("Activo" if usr.activo else "Inactivo")
            if usr.id != user.id:
                label = "Desactivar" if usr.activo else "Activar"
                if col_e.button(label, key=f"usr_{usr.id}"):
                    desactivar_usuario(usr.id)
                    st.rerun()
    else:
        st.info("No hay usuarios registrados")


@st.fragment
def dashboard_section():
    st.subheader("Filtrar datos")
    df_base = obtener_resumen_dashboard()
    todos_sectores = obtener_sectores()

    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        sec_filtro = st.selectbox(
            "Sector", [None] + todos_sectores,
            format_func=lambda x: "Todos" if x is None else x.nombre,
            key="filtro_sector"
        )
    with col_f2:
        lineas_filtro = []
        if sec_filtro:
            lineas_filtro = obtener_lineas_por_sector(sec_filtro.id)
        lin_filtro = st.selectbox(
            "Línea", [None] + lineas_filtro,
            format_func=lambda x: "Todas" if x is None else x.nombre,
            key="filtro_linea"
        )
    with col_f3:
        equipos_filtro = []
        if lin_filtro:
            equipos_filtro = obtener_equipos_por_linea(lin_filtro.id)
        eq_filtro = st.selectbox(
            "Equipo", [None] + equipos_filtro,
            format_func=lambda x: "Todos" if x is None else x.nombre,
            key="filtro_equipo"
        )

    df = df_base.copy()
    if sec_filtro:
        df = df[df["sector"] == sec_filtro.nombre]
    if lin_filtro:
        df = df[df["linea"] == lin_filtro.nombre]
    if eq_filtro:
        df = df[df["equipo"] == eq_filtro.nombre]

    st.markdown("---")

    col_g1, col_g2, col_g3 = st.columns(3)

    with col_g1:
        st.subheader("Por Sector")
        if not df.empty:
            grp = df.groupby("sector").agg(Cantidad=("equipo", "count"), Downtime=("duracion_minutos", "sum")).reset_index()
            chart = alt.Chart(grp).mark_bar(color="#4C78A8").encode(
                x=alt.X("sector:N", axis=alt.Axis(labelAngle=-45)),
                y=alt.Y("Cantidad:Q"),
            ).properties(height=250)
            st.altair_chart(chart, use_container_width=True)
        else:
            st.info("Sin datos")

    with col_g2:
        st.subheader("Por Línea")
        if not df.empty:
            grp = df.groupby("linea").agg(Cantidad=("equipo", "count"), Downtime=("duracion_minutos", "sum")).reset_index()
            chart = alt.Chart(grp).mark_bar(color="#E45756").encode(
                x=alt.X("linea:N", axis=alt.Axis(labelAngle=-45)),
                y=alt.Y("Cantidad:Q"),
            ).properties(height=250)
            st.altair_chart(chart, use_container_width=True)
        else:
            st.info("Sin datos")

    with col_g3:
        st.subheader("Por Equipo")
        if not df.empty:
            grp = df.groupby("equipo").agg(Cantidad=("equipo", "count"), Downtime=("duracion_minutos", "sum")).reset_index()
            top = grp.sort_values("Cantidad", ascending=False).head(10)
            chart = alt.Chart(top).mark_bar(color="#72B7B2").encode(
                x=alt.X("equipo:N", axis=alt.Axis(labelAngle=-45)),
                y=alt.Y("Cantidad:Q"),
            ).properties(height=250)
            st.altair_chart(chart, use_container_width=True)
        else:
            st.info("Sin datos")

    st.markdown("---")
    st.subheader("Detalle de paradas")
    todos_eventos = obtener_eventos()
    eventos_filt = todos_eventos
    if sec_filtro:
        eventos_filt = [e for e in eventos_filt if e.equipo and e.equipo.linea and e.equipo.linea.sector and e.equipo.linea.sector.nombre == sec_filtro.nombre]
    if lin_filtro:
        eventos_filt = [e for e in eventos_filt if e.equipo and e.equipo.linea and e.equipo.linea.nombre == lin_filtro.nombre]
    if eq_filtro:
        eventos_filt = [e for e in eventos_filt if e.equipo and e.equipo.nombre == eq_filtro.nombre]

    if eventos_filt:
        df_detalle = pd.DataFrame(
            [
                {
                    "Sector": e.equipo.linea.sector.nombre if e.equipo and e.equipo.linea and e.equipo.linea.sector else "",
                    "Línea": e.equipo.linea.nombre if e.equipo and e.equipo.linea else "",
                    "Equipo": e.equipo.nombre,
                    "Fecha": e.fecha,
                    "Hora": e.hora_inicio,
                    "Duración": fmt_duracion(e.duracion_minutos) if e.duracion_minutos else "",
                    "Falla": e.falla,
                    "Acción": e.accion,
                    "Técnico": e.tecnico,
                }
                for e in sorted(eventos_filt, key=lambda x: x.fecha or datetime.min, reverse=True)
            ]
        )
        st.dataframe(df_detalle, width="stretch")
    else:
        st.info("No hay paradas con los filtros seleccionados")


# =====================================
# NAVEGACIÓN
# =====================================

_pg_paradas = None

pages = [st.Page(page_inicio, title="Inicio", icon="🏠", default=True)]

if rol in ("admin", "tecnico", "operario"):
    _pg_paradas = st.Page(page_paradas, title="Registrar Parada", icon="➕")
    pages.append(_pg_paradas)

if rol in ("admin", "tecnico"):
    pages.append(st.Page(page_sectores, title="Sectores", icon="🏭"))
    pages.append(st.Page(page_lineas, title="Líneas", icon="📦"))
    pages.append(st.Page(page_equipos, title="Equipos", icon="🤖"))

if rol == "admin":
    pages.append(st.Page(page_repuestos, title="Repuestos", icon="🔩"))

if rol in ("admin", "tecnico", "operario", "produccion"):
    pages.append(st.Page(page_historial, title="Historial", icon="📋"))

if rol == "admin":
    pages.append(st.Page(page_usuarios, title="Usuarios", icon="👥"))

nav = st.navigation(pages, position="sidebar")
nav.run()

# Logout al pie del sidebar
if st.sidebar.button("Cerrar sesión", use_container_width=True):
    st.session_state.user = None
    st.rerun()

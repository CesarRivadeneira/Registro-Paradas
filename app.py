import json
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
    obtener_eventos_por_usuario,
    obtener_eventos_recientes,
    contar_eventos_mes,
    contar_eventos_por_equipo,
    contar_eventos_por_sector,
    repuestos_bajo_stock,
    sumar_duracion_total,
    sumar_duracion_mes,
    calcular_mttr_global,
    calcular_mtbf_global,
    calcular_kpi_por_linea,
    calcular_evolucion_mensual,
    crear_usuario,
    autenticar,
    hay_usuarios,
    obtener_usuarios,
    desactivar_usuario,
    crear_solicitud,
    obtener_solicitudes,
    programar_solicitud,
    completar_solicitud,
    rechazar_solicitud,
    editar_evento,
    guardar_permisos_extras,
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


PERMISOS_POR_ROL = {
    "admin": {
        "ver_sectores": True, "crear_sectores": True, "eliminar_sectores": True,
        "ver_lineas": True, "crear_lineas": True, "eliminar_lineas": True,
        "ver_equipos": True, "crear_equipos": True, "eliminar_equipos": True,
        "ver_repuestos": True, "crear_repuestos": True,
        "registrar_parada": True,
        "editar_parada_propia": True, "editar_parada_cualquiera": True,
        "ver_historial": True, "exportar_historial": True,
        "ver_solicitudes": True, "crear_solicitudes": True, "gestionar_solicitudes": True,
        "ver_usuarios": True, "gestionar_usuarios": True,
    },
    "supervisor": {
        "ver_sectores": True, "crear_sectores": False, "eliminar_sectores": False,
        "ver_lineas": True, "crear_lineas": False, "eliminar_lineas": False,
        "ver_equipos": True, "crear_equipos": False, "eliminar_equipos": False,
        "ver_repuestos": False, "crear_repuestos": False,
        "registrar_parada": True,
        "editar_parada_propia": True, "editar_parada_cualquiera": True,
        "ver_historial": True, "exportar_historial": False,
        "ver_solicitudes": True, "crear_solicitudes": True, "gestionar_solicitudes": True,
        "ver_usuarios": False, "gestionar_usuarios": False,
    },
    "tecnico": {
        "ver_sectores": True, "crear_sectores": False, "eliminar_sectores": False,
        "ver_lineas": True, "crear_lineas": False, "eliminar_lineas": False,
        "ver_equipos": True, "crear_equipos": False, "eliminar_equipos": False,
        "ver_repuestos": False, "crear_repuestos": False,
        "registrar_parada": True,
        "editar_parada_propia": True, "editar_parada_cualquiera": False,
        "ver_historial": True, "exportar_historial": False,
        "ver_solicitudes": True, "crear_solicitudes": True, "gestionar_solicitudes": False,
        "ver_usuarios": False, "gestionar_usuarios": False,
    },
    "operario": {
        "ver_sectores": False, "crear_sectores": False, "eliminar_sectores": False,
        "ver_lineas": False, "crear_lineas": False, "eliminar_lineas": False,
        "ver_equipos": False, "crear_equipos": False, "eliminar_equipos": False,
        "ver_repuestos": False, "crear_repuestos": False,
        "registrar_parada": True,
        "editar_parada_propia": True, "editar_parada_cualquiera": False,
        "ver_historial": True, "exportar_historial": False,
        "ver_solicitudes": True, "crear_solicitudes": True, "gestionar_solicitudes": False,
        "ver_usuarios": False, "gestionar_usuarios": False,
    },
    "produccion": {
        "ver_sectores": False, "crear_sectores": False, "eliminar_sectores": False,
        "ver_lineas": False, "crear_lineas": False, "eliminar_lineas": False,
        "ver_equipos": False, "crear_equipos": False, "eliminar_equipos": False,
        "ver_repuestos": False, "crear_repuestos": False,
        "registrar_parada": False,
        "editar_parada_propia": False, "editar_parada_cualquiera": False,
        "ver_historial": True, "exportar_historial": False,
        "ver_solicitudes": True, "crear_solicitudes": False, "gestionar_solicitudes": False,
        "ver_usuarios": False, "gestionar_usuarios": False,
    },
}

PERMISOS_DISPONIBLES = {
    "Sectores": ["ver_sectores", "crear_sectores", "eliminar_sectores"],
    "Líneas": ["ver_lineas", "crear_lineas", "eliminar_lineas"],
    "Equipos": ["ver_equipos", "crear_equipos", "eliminar_equipos"],
    "Repuestos": ["ver_repuestos", "crear_repuestos"],
    "Paradas": ["registrar_parada", "editar_parada_propia", "editar_parada_cualquiera"],
    "Historial": ["ver_historial", "exportar_historial"],
    "Solicitudes": ["ver_solicitudes", "crear_solicitudes", "gestionar_solicitudes"],
    "Usuarios": ["ver_usuarios", "gestionar_usuarios"],
}

_ETIQUETAS_PERMISOS = {
    "ver_sectores": "Ver sectores",
    "crear_sectores": "Crear sectores",
    "eliminar_sectores": "Eliminar sectores",
    "ver_lineas": "Ver líneas",
    "crear_lineas": "Crear líneas",
    "eliminar_lineas": "Eliminar líneas",
    "ver_equipos": "Ver equipos",
    "crear_equipos": "Crear equipos",
    "eliminar_equipos": "Eliminar equipos",
    "ver_repuestos": "Ver repuestos",
    "crear_repuestos": "Crear repuestos",
    "registrar_parada": "Registrar paradas",
    "editar_parada_propia": "Editar paradas propias",
    "editar_parada_cualquiera": "Editar cualquier parada",
    "ver_historial": "Ver historial",
    "exportar_historial": "Exportar historial a Excel",
    "ver_solicitudes": "Ver solicitudes",
    "crear_solicitudes": "Crear solicitudes",
    "gestionar_solicitudes": "Gestionar solicitudes (programar/completar/rechazar)",
    "ver_usuarios": "Ver usuarios",
    "gestionar_usuarios": "Gestionar usuarios (crear/activar/desactivar)",
}


def tiene_permiso(permiso):
    permisos = PERMISOS_POR_ROL.get(st.session_state.user.rol, {}).copy()
    extra = st.session_state.user.permisos_extra
    if extra:
        try:
            permisos.update(json.loads(extra))
        except (json.JSONDecodeError, TypeError):
            pass
    return permisos.get(permiso, False)


def puede_editar_parada(evento):
    if tiene_permiso("editar_parada_cualquiera"):
        return True
    if tiene_permiso("editar_parada_propia") and evento.user_id == st.session_state.user.id:
        return True
    return False


# =====================================
# CONFIG STREAMLIT
# =====================================

st.set_page_config(page_title="Gestión de Mantenimiento", layout="wide")

st.markdown(
    """
<style>
@media (min-width: 768px) {
  [data-testid="stToolbar"] { display: none; }
  [data-testid="stDecoration"] { display: none; }
}
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
        st.info("**Demo:** Usuario `upru` · Contraseña `p123123`")
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

    if tiene_permiso("crear_sectores"):
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

    if tiene_permiso("eliminar_sectores") and sectores:
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

    if tiene_permiso("crear_lineas"):
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

    if tiene_permiso("eliminar_lineas") and lineas:
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

    if tiene_permiso("crear_equipos"):
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

    if tiene_permiso("eliminar_equipos") and equipos:
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

    # --- EDITAR PARADA (propias) ---
    puede_editar = tiene_permiso("editar_parada_cualquiera") or tiene_permiso("editar_parada_propia")
    if puede_editar:
        st.markdown("---")
        st.header("Editar parada")
        if tiene_permiso("editar_parada_cualquiera"):
            eventos_propios = obtener_eventos()
        else:
            eventos_propios = obtener_eventos_por_usuario(user.id)

        editables = [e for e in eventos_propios if puede_editar_parada(e)]
        if editables:
            sel_e = st.selectbox(
                "Seleccionar parada a editar",
                editables,
                format_func=lambda x: f"#{x.id} — {x.equipo.nombre} ({x.fecha.strftime('%d/%m/%y')})",
                key="edit_parada_sel",
            )
            with st.form("form_editar_parada"):
                col_e1, col_e2 = st.columns(2)
                with col_e1:
                    nueva_fecha = st.date_input("Fecha", value=sel_e.fecha, key="ef_fecha")
                    nueva_hora = st.time_input("Hora inicio", value=None if not sel_e.hora_inicio else datetime.strptime(sel_e.hora_inicio, "%H:%M").time(), key="ef_hora")
                with col_e2:
                    dur_idx = 4
                    for i, (k, v) in enumerate(DURACION_OPTS.items()):
                        if v == sel_e.duracion_minutos:
                            dur_idx = i
                            break
                    nueva_duracion = st.selectbox("Duración", list(DURACION_OPTS.keys()), index=dur_idx, key="ef_duracion")
                nueva_falla = st.text_area("Falla", value=sel_e.falla, key="ef_falla")
                nueva_accion = st.text_area("Acción", value=sel_e.accion, key="ef_accion")
                repuestos = obtener_repuestos()
                rep_opts = [None] + repuestos
                rep_idx = 0
                for i, r in enumerate(rep_opts):
                    if r and sel_e.repuesto_id == r.id:
                        rep_idx = i
                        break
                nuevo_rep = st.selectbox(
                    "Repuesto",
                    rep_opts,
                    format_func=lambda x: "Ninguno" if x is None else f"{x.nombre} (stock: {x.stock})",
                    index=rep_idx,
                    key="ef_repuesto",
                )
                if st.form_submit_button("Guardar cambios", type="primary", use_container_width=True):
                    if not nueva_falla.strip():
                        st.error("La descripción de la falla es obligatoria")
                    elif not nueva_accion.strip():
                        st.error("La acción es obligatoria")
                    else:
                        hora_str = nueva_hora.strftime("%H:%M") if nueva_hora else ""
                        editar_evento(
                            sel_e.id,
                            datetime.combine(nueva_fecha, datetime.min.time()),
                            hora_str,
                            DURACION_OPTS[nueva_duracion],
                            nueva_falla.strip(),
                            nueva_accion.strip(),
                            nuevo_rep.id if nuevo_rep else None,
                        )
                        st.success("Parada actualizada correctamente")
                        st.rerun()
        else:
            st.info("No hay paradas disponibles para editar")


def page_historial():
    st.header("Historial")

    tab1, tab2 = st.tabs(["Paradas", "Solicitudes"])

    with tab1:
        st.subheader("Paradas de Mantenimiento")
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

        if not df_filtrado.empty and tiene_permiso("exportar_historial"):
            buffer = BytesIO()
            with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                df_filtrado.to_excel(writer, index=False, sheet_name="Paradas")
            st.download_button(
                label="Exportar a Excel",
                data=buffer.getvalue(),
                file_name=f"paradas_mantenimiento_{date.today()}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

    with tab2:
        st.subheader("Solicitudes de Reparación")
        solicitudes = obtener_solicitudes()
        if solicitudes:
            col_c1, col_c2, col_c3, col_c4 = st.columns(4)
            col_c1.metric("Pendientes", sum(1 for s in solicitudes if s.estado == "pendiente"))
            col_c2.metric("Programadas", sum(1 for s in solicitudes if s.estado == "programada"))
            col_c3.metric("Realizadas", sum(1 for s in solicitudes if s.estado == "realizada"))
            col_c4.metric("Rechazadas", sum(1 for s in solicitudes if s.estado == "rechazada"))

            estados = ["Todas", "pendiente", "programada", "realizada", "rechazada"]
            filtro_estado = st.selectbox("Filtrar por estado", estados, key="hist_sol_estado")
            solicitudes_filt = [s for s in solicitudes if filtro_estado == "Todas" or s.estado == filtro_estado]

            df_sol = pd.DataFrame([
                {
                    "ID": s.id,
                    "Fecha": s.fecha_solicitud.strftime("%d/%m/%y"),
                    "Línea": s.linea.nombre if s.linea else "",
                    "Equipo": s.equipo.nombre if s.equipo else "—",
                    "Solicitante": s.solicitante.nombre_completo or s.solicitante.username if s.solicitante else "",
                    "Estado": s.estado,
                    "Fecha Prog.": s.fecha_programada.strftime("%d/%m/%y") if s.fecha_programada else "—",
                    "Ejecución": s.fecha_ejecucion.strftime("%d/%m/%y") if s.fecha_ejecucion else "—",
                    "Observaciones": s.observaciones or "",
                    "Motivo Rechazo": s.motivo_rechazo or "",
                }
                for s in solicitudes_filt
            ])
            st.dataframe(df_sol, width="stretch")

            buffer = BytesIO()
            with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                df_sol.to_excel(writer, index=False, sheet_name="Solicitudes")
            st.download_button(
                label="Exportar solicitudes a Excel",
                data=buffer.getvalue(),
                file_name=f"solicitudes_reparacion_{date.today()}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        else:
            st.info("No hay solicitudes registradas")


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
                ["tecnico", "operario", "produccion", "supervisor"],
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
            with st.container():
                cols = st.columns([2, 2, 1, 1, 1])
                cols[0].write(usr.nombre_completo or usr.username)
                cols[1].write(usr.username)
                cols[2].write(usr.rol)
                cols[3].write("Activo" if usr.activo else "Inactivo")
                if usr.id != user.id:
                    label = "Desactivar" if usr.activo else "Activar"
                    if cols[4].button(label, key=f"usr_{usr.id}"):
                        desactivar_usuario(usr.id)
                        st.rerun()

                if usr.id != user.id:
                    with st.expander(f"Permisos — {usr.nombre_completo or usr.username}", key=f"perm_exp_{usr.id}"):
                        base_permisos = PERMISOS_POR_ROL.get(usr.rol, {}).copy()
                        actuales = base_permisos.copy()
                        if usr.permisos_extra:
                            try:
                                actuales.update(json.loads(usr.permisos_extra))
                            except (json.JSONDecodeError, TypeError):
                                pass

                        nuevos_extras = {}
                        st.markdown("**Permisos adicionales al rol**")
                        for categoria, lista in PERMISOS_DISPONIBLES.items():
                            with st.container():
                                st.markdown(f"**{categoria}**", help=None)
                                cols_p = st.columns(2)
                                for i, perm in enumerate(lista):
                                    etiqueta = _ETIQUETAS_PERMISOS.get(perm, perm)
                                    valor = st.checkbox(
                                        etiqueta, value=actuales.get(perm, False),
                                        key=f"perm_{usr.id}_{perm}"
                                    )
                                    if valor != base_permisos.get(perm, False):
                                        nuevos_extras[perm] = valor
                                    cols_p[i % 2].write("")

                                st.markdown("---", unsafe_allow_html=True)

                        if st.button("Guardar permisos", key=f"save_perm_{usr.id}"):
                            guardar_permisos_extras(usr.id, nuevos_extras or None)
                            st.success("Permisos guardados")
                            st.rerun()
    else:
        st.info("No hay usuarios registrados")


@st.fragment
def dashboard_section():
    from datetime import timedelta
    from database import get_db, Sector, Linea, Equipo, EventoMantenimiento

    # Selectores
    col_p1, col_p2, col_p3, col_p4 = st.columns([1, 1, 1, 1])
    with col_p1:
        periodo = st.selectbox("Período", ["Este mes", "Últimos 30 días", "Últimos 7 días"], key="kpi_periodo")
    with col_p2:
        modo = st.selectbox("Modo operativo", ["24/7", "24/5"], key="kpi_modo")
    with col_p4:
        pass

    hoy = date.today()
    if periodo == "Últimos 7 días":
        desde = hoy - timedelta(days=7)
    elif periodo == "Últimos 30 días":
        desde = hoy - timedelta(days=30)
    else:
        desde = hoy.replace(day=1)
    hasta = hoy

    # Métricas MTTR / MTBF
    mttr = calcular_mttr_global(desde, hasta)
    mtbf = calcular_mtbf_global(desde, hasta, modo)
    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    with col_m1:
        st.metric("MTTR", f"{mttr:.1f} h" if mttr else "—")
    with col_m2:
        st.metric("MTBF", f"{mtbf:.1f} h" if mtbf else "—")
    with col_m3:
        st.metric("Total Paradas", contar_eventos_mes())
    with col_m4:
        st.metric("Downtime total", fmt_duracion(sumar_duracion_total()))

    st.markdown("---")

    # KPIs por línea
    df_kpi = calcular_kpi_por_linea(desde, hasta, modo)
    if not df_kpi.empty:
        col_k1, col_k2 = st.columns(2)

        with col_k1:
            st.subheader("🔴 Peor MTTR por Línea")
            top_mttr = df_kpi.nlargest(10, "mttr_h")
            chart = alt.Chart(top_mttr).mark_bar(color="#E45756").encode(
                y=alt.Y("linea:N", title=None, sort=alt.EncodingSortField("mttr_h", order="descending")),
                x=alt.X("mttr_h:Q", title="Horas"),
                tooltip=["linea", "mttr_h", "fallas"],
            ).properties(height=250)
            st.altair_chart(chart, use_container_width=True)

        with col_k2:
            st.subheader("🔴 Peor MTBF por Línea")
            top_mtbf = df_kpi.nsmallest(10, "mtbf_h")
            chart = alt.Chart(top_mtbf).mark_bar(color="#4C78A8").encode(
                y=alt.Y("linea:N", title=None, sort=alt.EncodingSortField("mtbf_h", order="ascending")),
                x=alt.X("mtbf_h:Q", title="Horas"),
                tooltip=["linea", "mtbf_h", "fallas"],
            ).properties(height=250)
            st.altair_chart(chart, use_container_width=True)

        st.markdown("---")
        st.subheader("KPIs por Línea (todas)")
        st.dataframe(
            df_kpi.rename(columns={
                "sector": "Sector", "linea": "Línea", "fallas": "Fallas",
                "downtime_min": "Downtime (min)", "mttr_h": "MTTR (h)", "mtbf_h": "MTBF (h)"
            }),
            width="stretch",
        )
        st.markdown("---")

    # Evolución mensual
    st.subheader("📈 Evolución MTTR / MTBF (12 meses)")
    df_evol = calcular_evolucion_mensual(modo)
    if not df_evol.empty:
        df_evol["mes_label"] = pd.to_datetime(df_evol["mes"]).dt.strftime("%b %y")
        df_long = df_evol.melt(
            id_vars=["mes_label"],
            value_vars=["mttr_h", "mtbf_h"],
            var_name="Medida", value_name="Horas",
        )
        chart = alt.Chart(df_long).mark_line(point=True).encode(
            x=alt.X("mes_label:N", title=None, sort=None),
            y=alt.Y("Horas:Q", title="Horas"),
            color=alt.Color("Medida:N", legend=alt.Legend(title=None)),
            tooltip=["mes_label", "Horas", "Medida"],
        ).properties(height=300)
        st.altair_chart(chart, use_container_width=True)
    else:
        st.info("Sin datos históricos suficientes")

    st.markdown("---")

    # Filtros por Sector / Línea / Equipo
    st.subheader("Filtrar datos")
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

    # Cargar datos para gráficos y tabla
    with get_db() as db:
        base_rows = (
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
    df_base = pd.DataFrame(base_rows, columns=["sector", "linea", "equipo", "duracion_minutos"])
    df_f = df_base.copy()
    if sec_filtro:
        df_f = df_f[df_f["sector"] == sec_filtro.nombre]
    if lin_filtro:
        df_f = df_f[df_f["linea"] == lin_filtro.nombre]
    if eq_filtro:
        df_f = df_f[df_f["equipo"] == eq_filtro.nombre]

    col_g1, col_g2, col_g3 = st.columns(3)
    with col_g1:
        st.subheader("Por Sector")
        if not df_f.empty:
            grp = df_f.groupby("sector").agg(Cantidad=("equipo", "count"), Downtime=("duracion_minutos", "sum")).reset_index()
            st.altair_chart(alt.Chart(grp).mark_bar(color="#4C78A8").encode(
                x=alt.X("sector:N", axis=alt.Axis(labelAngle=-45)),
                y=alt.Y("Cantidad:Q"),
            ).properties(height=250), use_container_width=True)
        else:
            st.info("Sin datos")

    with col_g2:
        st.subheader("Por Línea")
        if not df_f.empty:
            grp = df_f.groupby("linea").agg(Cantidad=("equipo", "count"), Downtime=("duracion_minutos", "sum")).reset_index()
            st.altair_chart(alt.Chart(grp).mark_bar(color="#E45756").encode(
                x=alt.X("linea:N", axis=alt.Axis(labelAngle=-45)),
                y=alt.Y("Cantidad:Q"),
            ).properties(height=250), use_container_width=True)
        else:
            st.info("Sin datos")

    with col_g3:
        st.subheader("Por Equipo")
        if not df_f.empty:
            grp = df_f.groupby("equipo").agg(Cantidad=("equipo", "count"), Downtime=("duracion_minutos", "sum")).reset_index()
            top = grp.sort_values("Cantidad", ascending=False).head(10)
            st.altair_chart(alt.Chart(top).mark_bar(color="#72B7B2").encode(
                x=alt.X("equipo:N", axis=alt.Axis(labelAngle=-45)),
                y=alt.Y("Cantidad:Q"),
            ).properties(height=250), use_container_width=True)
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


def page_solicitudes():
    st.header("Solicitudes de Reparación")

    if tiene_permiso("crear_solicitudes"):
        with st.expander("Nueva solicitud", expanded=True):
            sectores = obtener_sectores()
            if sectores:
                sector_sel = st.selectbox(
                    "Sector", sectores, format_func=lambda x: x.nombre,
                    key="sol_sector"
                )
                lineas_del_sector = obtener_lineas_por_sector(sector_sel.id)
                if lineas_del_sector:
                    linea_sel = st.selectbox(
                        "Línea", lineas_del_sector, format_func=lambda x: x.nombre,
                        key="sol_linea"
                    )
                    equipos_de_linea = obtener_equipos_por_linea(linea_sel.id)
                    equipo_sel = st.selectbox(
                        "Equipo (opcional)",
                        [None] + equipos_de_linea,
                        format_func=lambda x: "— Toda la línea —" if x is None else f"{x.nombre} ({x.tipo})",
                        key="sol_equipo"
                    )
                    descripcion = st.text_area("Descripción de la reparación necesaria")
                    if st.button("Solicitar reparación", use_container_width=True):
                        if not descripcion.strip():
                            st.error("La descripción es obligatoria")
                        else:
                            crear_solicitud(
                                linea_sel.id,
                                descripcion.strip(),
                                user.id,
                                equipo_id=equipo_sel.id if equipo_sel else None,
                            )
                            st.success("Solicitud creada correctamente")
                            st.rerun()
                else:
                    st.info("No hay líneas en este sector")
            else:
                st.info("No hay sectores registrados")

    st.markdown("---")
    st.subheader("Todas las solicitudes")

    solicitudes = obtener_solicitudes()
    if not solicitudes:
        st.info("No hay solicitudes registradas")
        return

    estados_opts = ["Todas", "pendiente", "programada", "realizada", "rechazada"]
    filtro_estado = st.selectbox("Filtrar por estado", estados_opts, key="sol_filtro")

    solicitudes_filt = [s for s in solicitudes if filtro_estado == "Todas" or s.estado == filtro_estado]

    df = pd.DataFrame([
        {
            "ID": s.id,
            "Fecha": s.fecha_solicitud.strftime("%d/%m/%y"),
            "Línea": s.linea.nombre if s.linea else "",
            "Equipo": s.equipo.nombre if s.equipo else "—",
            "Solicitante": s.solicitante.nombre_completo or s.solicitante.username if s.solicitante else "",
            "Estado": s.estado,
            "Fecha Prog.": s.fecha_programada.strftime("%d/%m/%y") if s.fecha_programada else "—",
            "Ejecutada": s.fecha_ejecucion.strftime("%d/%m/%y") if s.fecha_ejecucion else "—",
        }
        for s in solicitudes_filt
    ])
    st.dataframe(df, width="stretch")

    if tiene_permiso("gestionar_solicitudes") and solicitudes_filt:
        st.markdown("---")
        st.subheader("Gestionar solicitud")

        sol_keys = {
            s.id: f"#{s.id} — {s.linea.nombre if s.linea else ''} ({s.estado})"
            for s in solicitudes_filt
        }
        sel_id = st.selectbox(
            "Seleccionar solicitud", list(sol_keys.keys()),
            format_func=lambda x: sol_keys[x], key="sol_gestion"
        )
        sol_sel = next((s for s in solicitudes_filt if s.id == sel_id), None)
        if sol_sel:
            st.write(f"**Descripción:** {sol_sel.descripcion}")

            if sol_sel.estado == "pendiente":
                col_p1, col_p2 = st.columns(2)
                with col_p1:
                    fecha = st.date_input("Fecha programada para la intervención", key="prog_fecha")
                    if st.button("📅 Programar solicitud", use_container_width=True):
                        programar_solicitud(
                            sol_sel.id, datetime.combine(fecha, datetime.min.time()), user.id
                        )
                        st.success("Solicitud programada")
                        st.rerun()
                with col_p2:
                    with st.form("rechazar_form"):
                        motivo = st.text_area("Motivo del rechazo")
                        if st.form_submit_button("❌ Rechazar solicitud", type="primary", use_container_width=True):
                            if not motivo.strip():
                                st.error("Debe indicar el motivo del rechazo")
                            else:
                                rechazar_solicitud(sol_sel.id, user.id, motivo.strip())
                                st.success("Solicitud rechazada")
                                st.rerun()

            elif sol_sel.estado == "programada":
                with st.form("completar_form"):
                    obs = st.text_area("Observaciones (opcional)")
                    if st.form_submit_button("✅ Completar solicitud", type="primary", use_container_width=True):
                        completar_solicitud(sol_sel.id, user.id, obs.strip())
                        st.success("Solicitud completada")
                        st.rerun()

            elif sol_sel.estado == "rechazada":
                st.warning(f"**Motivo de rechazo:** {sol_sel.motivo_rechazo}")
            elif sol_sel.estado == "realizada":
                if sol_sel.observaciones:
                    st.info(f"**Observaciones:** {sol_sel.observaciones}")


# =====================================
# NAVEGACIÓN
# =====================================

_pg_paradas = None

pages = [st.Page(page_inicio, title="Inicio", icon="🏠", default=True)]

if tiene_permiso("registrar_parada"):
    _pg_paradas = st.Page(page_paradas, title="Registrar Parada", icon="➕")
    pages.append(_pg_paradas)

if tiene_permiso("ver_sectores"):
    pages.append(st.Page(page_sectores, title="Sectores", icon="🏭"))
if tiene_permiso("ver_lineas"):
    pages.append(st.Page(page_lineas, title="Líneas", icon="📦"))
if tiene_permiso("ver_equipos"):
    pages.append(st.Page(page_equipos, title="Equipos", icon="🤖"))

if tiene_permiso("ver_repuestos"):
    pages.append(st.Page(page_repuestos, title="Repuestos", icon="🔩"))

if tiene_permiso("ver_solicitudes"):
    pages.append(st.Page(page_solicitudes, title="Solicitudes", icon="🔧"))

if tiene_permiso("ver_historial"):
    pages.append(st.Page(page_historial, title="Historial", icon="📋"))

if tiene_permiso("ver_usuarios"):
    pages.append(st.Page(page_usuarios, title="Usuarios", icon="👥"))

nav = st.navigation(pages, position="sidebar")
nav.run()

# Logout al pie del sidebar
if st.sidebar.button("Cerrar sesión", use_container_width=True):
    st.session_state.user = None
    st.rerun()

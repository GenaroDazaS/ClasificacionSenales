from __future__ import annotations

import os
from datetime import datetime, time
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st

from db import (
    create_attempt,
    get_competition_settings,
    get_student,
    has_competition_attempt,
    init_db,
    load_attempt,
    load_dashboard_data,
    save_response,
    update_competition_settings,
    upsert_student,
)
from game_data import get_level, levels
from ui import answer_form, evaluate_answers, hero, inject_css, render_result, signal_figure

TZ = ZoneInfo("America/Bogota")
TOTAL_LEVELS = 5

st.set_page_config(
    page_title="Reto de Clasificación de Señales",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_css()
init_db()


def local_now() -> datetime:
    return datetime.now(TZ).replace(tzinfo=None)


def parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except Exception:
        return None


def competition_is_currently_valid(code_entered: str) -> tuple[bool, str]:
    settings = get_competition_settings()
    if not bool(settings["active"]):
        return False, "La competencia no está activa en este momento."
    expected_code = str(settings["competition_code"] or "").strip()
    if expected_code and code_entered.strip() != expected_code:
        return False, "El código de competencia no es correcto."
    now = local_now()
    start_at = parse_dt(settings.get("start_at"))
    end_at = parse_dt(settings.get("end_at"))
    if start_at and now < start_at:
        return False, "La competencia todavía no ha iniciado."
    if end_at and now > end_at:
        return False, "La competencia ya finalizó."
    return True, "Competencia activa."


def init_session_defaults() -> None:
    defaults = {
        "student": None,
        "attempt_id": None,
        "mode": None,
        "current_level": 1,
        "last_result": None,
        "level_answered": False,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


init_session_defaults()


with st.sidebar:
    st.title("📈 Señales")
    page = st.radio("Seleccione una vista", ["Estudiante", "Profesor"], index=0)
    st.divider()
    st.caption("Reto de clasificación de señales de tiempo continuo.")


if page == "Estudiante":
    hero(
        "Reto de Clasificación de Señales",
        "Observe la señal, analice sus propiedades y supere los 5 niveles."
    )

    if st.session_state.student is None:
        st.subheader("Registro del estudiante")
        st.info("Los datos registrados se usarán únicamente con fines académicos para identificar el desempeño en la actividad.")
        with st.form("student_registration"):
            col1, col2 = st.columns(2)
            with col1:
                name = st.text_input("Nombre completo")
                student_code = st.text_input("Código estudiantil")
            with col2:
                email = st.text_input("Correo institucional")
                group_name = st.text_input("Grupo / curso", value="Introducción a señales y sistemas")
            submitted = st.form_submit_button("Registrar e iniciar")

        if submitted:
            if not name.strip() or not student_code.strip() or not email.strip():
                st.error("Complete nombre, código y correo para continuar.")
            else:
                upsert_student(name, student_code, email, group_name)
                st.session_state.student = get_student(student_code.strip())
                st.success("Registro completado.")
                st.rerun()
    else:
        student = st.session_state.student
        st.markdown(f"<span class='info-pill'>Estudiante: {student['name']} | Código: {student['student_code']}</span>", unsafe_allow_html=True)

        if st.session_state.attempt_id is None:
            st.subheader("Seleccione el modo de uso")
            settings = get_competition_settings()
            comp_active = bool(settings["active"])
            already_competed = has_competition_attempt(student["student_code"])

            c1, c2 = st.columns(2)
            with c1:
                st.markdown("### 🧪 Modo práctica")
                st.write("Disponible en cualquier momento. Puede repetirlo para estudiar. No cuenta para premiación.")
                if st.button("Iniciar práctica"):
                    st.session_state.attempt_id = create_attempt(
                        student_code=student["student_code"],
                        mode="práctica",
                        competition_valid=False,
                        metadata={"source": "student_practice"},
                    )
                    st.session_state.mode = "práctica"
                    st.session_state.current_level = 1
                    st.session_state.level_answered = False
                    st.session_state.last_result = None
                    st.rerun()
            with c2:
                st.markdown("### 🏆 Modo competencia")
                if already_competed:
                    st.warning("Ya registró su único intento de competencia. Puede seguir usando el modo práctica.")
                elif not comp_active:
                    st.warning("La competencia no está activa. Espere la activación del profesor.")
                else:
                    st.write("Solo puede ejecutarse una vez y cuenta para la premiación.")
                    code_entered = st.text_input("Código de competencia", type="password")
                    valid, message = competition_is_currently_valid(code_entered)
                    st.caption(message)
                    if st.button("Iniciar competencia"):
                        valid, message = competition_is_currently_valid(code_entered)
                        if valid and not has_competition_attempt(student["student_code"]):
                            st.session_state.attempt_id = create_attempt(
                                student_code=student["student_code"],
                                mode="competencia",
                                competition_valid=True,
                                metadata={"source": "student_competition"},
                            )
                            st.session_state.mode = "competencia"
                            st.session_state.current_level = 1
                            st.session_state.level_answered = False
                            st.session_state.last_result = None
                            st.rerun()
                        else:
                            st.error(message)
        else:
            attempt = load_attempt(st.session_state.attempt_id)
            if not attempt:
                st.error("No se encontró el intento actual. Reinicie la aplicación.")
                st.stop()

            level_number = int(st.session_state.current_level)
            if attempt["status"] == "completed" or level_number > TOTAL_LEVELS:
                st.subheader("Resultado final")
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Modo", attempt["mode"])
                c2.metric("Niveles perfectos", f"{attempt['perfect_levels']}/{TOTAL_LEVELS}")
                c3.metric("Puntaje", f"{attempt['final_score']:.1f}%")
                c4.metric("Ganador", "Sí" if attempt["winner"] else "No")

                if attempt["winner"]:
                    st.success("¡Reto completado con clasificación perfecta en los 5 niveles!")
                    st.balloons()
                else:
                    st.warning("El reto fue registrado. Puede seguir practicando para reforzar los conceptos.")

                if st.button("Volver al inicio"):
                    st.session_state.attempt_id = None
                    st.session_state.mode = None
                    st.session_state.current_level = 1
                    st.session_state.level_answered = False
                    st.session_state.last_result = None
                    st.rerun()
            else:
                signal = get_level(level_number)
                st.progress((level_number - 1) / TOTAL_LEVELS, text=f"Nivel {level_number} de {TOTAL_LEVELS}")
                c1, c2, c3 = st.columns(3)
                c1.metric("Modo", st.session_state.mode)
                c2.metric("Nivel actual", f"{level_number}/{TOTAL_LEVELS}")
                c3.metric("Estado", "Competencia" if st.session_state.mode == "competencia" else "Práctica")

                left, right = st.columns([1.15, 1])
                with left:
                    st.subheader(signal.title)
                    st.caption(signal.subtitle)
                    st.plotly_chart(signal_figure(signal), use_container_width=True)
                    st.latex(signal.equation)
                with right:
                    st.subheader("Clasifique la señal")
                    answers = answer_form(signal, key_prefix=f"attempt_{st.session_state.attempt_id}")
                    if st.button("Enviar clasificación", disabled=st.session_state.level_answered):
                        result_details, correct_count, total_count, is_perfect = evaluate_answers(
                            answers, signal.answers, signal.explanations
                        )
                        save_response(
                            attempt_id=st.session_state.attempt_id,
                            student_code=student["student_code"],
                            level=signal.level,
                            signal_id=signal.signal_id,
                            answers=answers,
                            correct_answers=signal.answers,
                            result_details=result_details,
                            correct_count=correct_count,
                            total_count=total_count,
                            is_perfect=is_perfect,
                        )
                        st.session_state.last_result = {
                            "details": result_details,
                            "correct_count": correct_count,
                            "total_count": total_count,
                            "is_perfect": is_perfect,
                        }
                        st.session_state.level_answered = True
                        st.rerun()

                if st.session_state.last_result:
                    st.divider()
                    st.subheader("Retroalimentación")
                    render_result(
                        st.session_state.last_result["details"],
                        st.session_state.last_result["correct_count"],
                        st.session_state.last_result["total_count"],
                        st.session_state.last_result["is_perfect"],
                    )
                    if st.button("Continuar al siguiente nivel"):
                        st.session_state.current_level += 1
                        st.session_state.level_answered = False
                        st.session_state.last_result = None
                        st.rerun()

elif page == "Profesor":
    hero("Panel del profesor", "Active la competencia, consulte resultados y descargue el desempeño de los estudiantes.")

    try:
        default_password = st.secrets.get("TEACHER_PASSWORD", "admin123")
    except Exception:
        default_password = os.environ.get("TEACHER_PASSWORD", "admin123")

    if "teacher_auth" not in st.session_state:
        st.session_state.teacher_auth = False

    if not st.session_state.teacher_auth:
        password = st.text_input("Contraseña del profesor", type="password")
        if st.button("Ingresar"):
            if password == default_password:
                st.session_state.teacher_auth = True
                st.rerun()
            else:
                st.error("Contraseña incorrecta.")
        st.stop()

    tab1, tab2, tab3 = st.tabs(["Control de competencia", "Resultados", "Detalle de respuestas"])

    with tab1:
        st.subheader("Control de competencia")
        settings = get_competition_settings()
        active = st.toggle("Competencia activa", value=bool(settings["active"]))
        competition_code = st.text_input("Código de competencia", value=str(settings["competition_code"] or "SENALES"))

        col1, col2 = st.columns(2)
        with col1:
            st.write("Inicio de competencia")
            start_date = st.date_input("Fecha de inicio", value=local_now().date(), key="start_date")
            start_time = st.time_input("Hora de inicio", value=time(8, 0), key="start_time")
        with col2:
            st.write("Cierre de competencia")
            end_date = st.date_input("Fecha de cierre", value=local_now().date(), key="end_date")
            end_time = st.time_input("Hora de cierre", value=time(23, 59), key="end_time")

        if st.button("Guardar configuración"):
            start_at = datetime.combine(start_date, start_time).isoformat(timespec="minutes")
            end_at = datetime.combine(end_date, end_time).isoformat(timespec="minutes")
            update_competition_settings(active, competition_code, start_at, end_at)
            st.success("Configuración guardada.")
            st.rerun()

        current = get_competition_settings()
        st.info(
            f"Estado actual: {'Activa' if current['active'] else 'Inactiva'} | "
            f"Código: {current['competition_code']} | "
            f"Inicio: {current['start_at']} | Cierre: {current['end_at']}"
        )

    with tab2:
        st.subheader("Resultados generales")
        attempts, responses = load_dashboard_data()
        if attempts.empty:
            st.warning("Todavía no hay intentos registrados.")
        else:
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Estudiantes con intentos", attempts["student_code"].nunique())
            col2.metric("Intentos registrados", len(attempts))
            col3.metric("Intentos de competencia", int(((attempts["mode"] == "competencia") & (attempts["competition_valid"] == 1)).sum()))
            col4.metric("Ganadores", int(attempts["winner"].sum()))

            mode_filter = st.selectbox("Filtrar por modo", ["Todos", "competencia", "práctica"])
            df = attempts.copy()
            if mode_filter != "Todos":
                df = df[df["mode"] == mode_filter]

            only_valid = st.checkbox("Solo competencia válida", value=False)
            if only_valid:
                df = df[(df["mode"] == "competencia") & (df["competition_valid"] == 1)]

            rank = df.sort_values(by=["winner", "completed_at", "final_score"], ascending=[False, True, False])
            display_cols = [
                "name", "student_code", "email", "group_name", "mode", "competition_valid",
                "started_at", "completed_at", "levels_completed", "perfect_levels", "final_score", "winner", "status"
            ]
            st.dataframe(rank[display_cols], use_container_width=True)
            st.download_button(
                "Descargar resultados generales CSV",
                data=rank[display_cols].to_csv(index=False).encode("utf-8"),
                file_name="resultados_generales_senales.csv",
                mime="text/csv",
            )

    with tab3:
        st.subheader("Detalle de respuestas por nivel")
        attempts, responses = load_dashboard_data()
        if responses.empty:
            st.warning("Todavía no hay respuestas registradas.")
        else:
            display_cols = [
                "submitted_at", "name", "student_code", "email", "group_name", "mode",
                "competition_valid", "attempt_id", "level", "signal_id", "correct_count", "total_count", "is_perfect",
                "answers", "correct_answers"
            ]
            st.dataframe(responses[display_cols], use_container_width=True)
            st.download_button(
                "Descargar detalle CSV",
                data=responses[display_cols].to_csv(index=False).encode("utf-8"),
                file_name="detalle_respuestas_senales.csv",
                mime="text/csv",
            )

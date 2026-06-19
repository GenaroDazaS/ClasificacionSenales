from __future__ import annotations

from typing import Dict, List

import numpy as np
import plotly.graph_objects as go
import streamlit as st

from game_data import CATEGORIES, CATEGORY_LABELS, SignalLevel


def inject_css() -> None:
    st.markdown(
        """
        <style>
        .stApp {
            background: radial-gradient(circle at top left, #13294B 0%, #08111F 45%, #050A12 100%);
            color: #F4F7FB;
        }
        h1, h2, h3 { color: #F4F7FB !important; }
        .block-container { padding-top: 2rem; padding-bottom: 3rem; max-width: 1250px; }
        .hero-card {
            padding: 1.3rem 1.5rem;
            border-radius: 22px;
            background: linear-gradient(135deg, rgba(37, 99, 235, 0.28), rgba(14, 165, 233, 0.16));
            border: 1px solid rgba(255,255,255,0.16);
            box-shadow: 0 18px 50px rgba(0,0,0,0.25);
            margin-bottom: 1rem;
        }
        .game-card {
            padding: 1.2rem;
            border-radius: 18px;
            background: rgba(255,255,255,0.07);
            border: 1px solid rgba(255,255,255,0.14);
            box-shadow: 0 12px 30px rgba(0,0,0,0.18);
            margin-bottom: 1rem;
        }
        .success-pill, .danger-pill, .warn-pill, .info-pill {
            display: inline-block;
            padding: 0.22rem 0.55rem;
            border-radius: 999px;
            font-weight: 700;
            font-size: 0.85rem;
            margin: 0.1rem 0;
        }
        .success-pill { background: #DCFCE7; color: #166534; }
        .danger-pill { background: #FEE2E2; color: #991B1B; }
        .warn-pill { background: #FEF3C7; color: #92400E; }
        .info-pill { background: #DBEAFE; color: #1E40AF; }
        .small-muted { color: #B8C4D6; font-size: 0.92rem; }
        div[data-testid="stMetric"] {
            background: rgba(255,255,255,0.08);
            border: 1px solid rgba(255,255,255,0.12);
            padding: 1rem;
            border-radius: 16px;
        }
        .stButton>button {
            border-radius: 999px;
            font-weight: 700;
            border: 0;
            background: linear-gradient(135deg, #38BDF8, #2563EB);
            color: white;
            padding: 0.6rem 1.2rem;
        }
        .stDownloadButton>button {
            border-radius: 999px;
            font-weight: 700;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def hero(title: str, subtitle: str) -> None:
    st.markdown(
        f"""
        <div class="hero-card">
            <h1 style="margin-bottom: 0.2rem;">{title}</h1>
            <div class="small-muted">{subtitle}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def card_start() -> None:
    st.markdown('<div class="game-card">', unsafe_allow_html=True)


def card_end() -> None:
    st.markdown('</div>', unsafe_allow_html=True)


def signal_figure(signal: SignalLevel) -> go.Figure:
    t = np.linspace(signal.t_min, signal.t_max, 1600)
    y = signal.func(t)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=t, y=y, mode="lines", line=dict(width=4), name="x(t)"))
    fig.add_hline(y=0, line_width=1, line_dash="solid", line_color="rgba(255,255,255,0.55)")
    fig.add_vline(x=0, line_width=1, line_dash="solid", line_color="rgba(255,255,255,0.55)")
    fig.update_layout(
        template="plotly_dark",
        height=390,
        margin=dict(l=30, r=20, t=35, b=35),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(255,255,255,0.04)",
        title="Gráfica de la señal",
        xaxis_title="t [s]",
        yaxis_title="x(t)",
        xaxis=dict(range=[signal.t_min, signal.t_max], zeroline=False, gridcolor="rgba(255,255,255,0.12)"),
        yaxis=dict(range=[signal.y_min, signal.y_max], zeroline=False, gridcolor="rgba(255,255,255,0.12)"),
        showlegend=False,
    )
    return fig


def answer_form(signal: SignalLevel, key_prefix: str) -> Dict[str, str]:
    answers: Dict[str, str] = {}
    for category, options in CATEGORIES.items():
        answers[category] = st.radio(
            CATEGORY_LABELS[category],
            options,
            horizontal=True,
            key=f"{key_prefix}_{signal.level}_{category}",
        )
    return answers


def evaluate_answers(user_answers: Dict[str, str], correct_answers: Dict[str, str], explanations: Dict[str, str]) -> tuple[List[Dict], int, int, bool]:
    result_details = []
    correct_count = 0
    for category, correct in correct_answers.items():
        selected = user_answers.get(category, "")
        ok = selected == correct
        if ok:
            correct_count += 1
        result_details.append({
            "category": category,
            "label": CATEGORY_LABELS[category],
            "selected": selected,
            "correct": correct,
            "is_correct": ok,
            "explanation": explanations[category],
        })
    total = len(correct_answers)
    return result_details, correct_count, total, correct_count == total


def render_result(result_details: List[Dict], correct_count: int, total: int, is_perfect: bool) -> None:
    if is_perfect:
        st.success(f"Clasificación perfecta: {correct_count}/{total}. ¡Nivel superado!")
        st.balloons()
    else:
        st.warning(f"Resultado del nivel: {correct_count}/{total}. Revise las categorías marcadas en rojo.")

    for item in result_details:
        pill = "success-pill" if item["is_correct"] else "danger-pill"
        label = "Correcto" if item["is_correct"] else "Incorrecto"
        st.markdown(
            f"""
            <div class="game-card">
                <b>{item['label']}</b><br>
                <span class="{pill}">{label}</span><br>
                <span class="small-muted">Tu respuesta: <b>{item['selected']}</b></span><br>
                <span class="small-muted">Respuesta correcta: <b>{item['correct']}</b></span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if not item["is_correct"]:
            with st.expander(f"¿Por qué en {item['label']} no es correcto?"):
                st.write(item["explanation"])

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List, Tuple

import numpy as np

CATEGORIES = {
    "dominio": ["Tiempo continuo", "Tiempo discreto"],
    "amplitud": ["Análoga", "Digital"],
    "valores": ["Real", "Compleja"],
    "periodicidad": ["Periódica", "Aperiódica"],
    "paridad": ["Par", "Impar", "Ninguna"],
    "tipo_energetico": ["Energía", "Potencia", "Ninguna"],
    "causalidad": ["Causal", "No causal"],
}

CATEGORY_LABELS = {
    "dominio": "Dominio de la variable independiente",
    "amplitud": "Naturaleza de la amplitud",
    "valores": "Naturaleza de los valores",
    "periodicidad": "Periodicidad",
    "paridad": "Paridad",
    "tipo_energetico": "Tipo energético",
    "causalidad": "Causalidad",
}


@dataclass(frozen=True)
class SignalLevel:
    level: int
    signal_id: str
    title: str
    subtitle: str
    equation: str
    t_min: float
    t_max: float
    y_min: float
    y_max: float
    func: Callable[[np.ndarray], np.ndarray]
    answers: Dict[str, str]
    explanations: Dict[str, str]


def u(t: np.ndarray) -> np.ndarray:
    return (t >= 0).astype(float)


def levels() -> List[SignalLevel]:
    return [
        SignalLevel(
            level=1,
            signal_id="sinusoidal_cos",
            title="Nivel 1: señal sinusoidal",
            subtitle="Identifique propiedades básicas de una señal oscilatoria.",
            equation=r"x(t)=2\cos(\pi t)",
            t_min=-4,
            t_max=4,
            y_min=-2.5,
            y_max=2.5,
            func=lambda t: 2 * np.cos(np.pi * t),
            answers={
                "dominio": "Tiempo continuo",
                "amplitud": "Análoga",
                "valores": "Real",
                "periodicidad": "Periódica",
                "paridad": "Par",
                "tipo_energetico": "Potencia",
                "causalidad": "No causal",
            },
            explanations={
                "dominio": "La señal está definida como función de la variable continua t, no como una secuencia x[n].",
                "amplitud": "La amplitud puede tomar valores continuos dentro de un intervalo, por eso se clasifica como análoga.",
                "valores": "La expresión solo involucra el coseno real; no aparece una componente imaginaria.",
                "periodicidad": "El coseno se repite regularmente. En este caso, existe T>0 tal que x(t)=x(t+T).",
                "paridad": "Como cos(·) es una función par y no hay desplazamiento de fase, se cumple x(-t)=x(t).",
                "tipo_energetico": "Una señal sinusoidal no nula tiene energía infinita y potencia promedio finita; por eso es señal de potencia.",
                "causalidad": "No es causal porque tiene valores distintos de cero para tiempos negativos.",
            },
        ),
        SignalLevel(
            level=2,
            signal_id="exp_causal",
            title="Nivel 2: exponencial decreciente causal",
            subtitle="Analice causalidad y tipo energético.",
            equation=r"x(t)=e^{-t}u(t)",
            t_min=-2,
            t_max=6,
            y_min=-0.2,
            y_max=1.2,
            func=lambda t: np.exp(-t) * u(t),
            answers={
                "dominio": "Tiempo continuo",
                "amplitud": "Análoga",
                "valores": "Real",
                "periodicidad": "Aperiódica",
                "paridad": "Ninguna",
                "tipo_energetico": "Energía",
                "causalidad": "Causal",
            },
            explanations={
                "dominio": "La señal se describe mediante una función de tiempo continuo t.",
                "amplitud": "Sus valores de amplitud no están cuantizados en un conjunto discreto de niveles.",
                "valores": "La señal toma valores reales positivos o cero.",
                "periodicidad": "La exponencial decreciente causal no repite su forma de manera indefinida.",
                "paridad": "No cumple x(-t)=x(t) ni x(-t)=-x(t), principalmente por el escalón unitario.",
                "tipo_energetico": "La integral de |e^{-t}u(t)|^2 en todo el tiempo es finita, por eso es señal de energía.",
                "causalidad": "Es cero para t<0; por tanto, se clasifica como causal.",
            },
        ),
        SignalLevel(
            level=3,
            signal_id="triangular_even",
            title="Nivel 3: señal triangular centrada",
            subtitle="Observe soporte finito y simetría par.",
            equation=r"x(t)=\begin{cases}1-\frac{|t|}{2}, & |t|\leq 2\\0, & |t|>2\end{cases}",
            t_min=-4,
            t_max=4,
            y_min=-0.2,
            y_max=1.2,
            func=lambda t: np.where(np.abs(t) <= 2, 1 - np.abs(t) / 2, 0),
            answers={
                "dominio": "Tiempo continuo",
                "amplitud": "Análoga",
                "valores": "Real",
                "periodicidad": "Aperiódica",
                "paridad": "Par",
                "tipo_energetico": "Energía",
                "causalidad": "No causal",
            },
            explanations={
                "dominio": "La señal se representa sobre un eje temporal continuo.",
                "amplitud": "La amplitud varía de manera continua dentro de los tramos lineales.",
                "valores": "No contiene componente imaginaria.",
                "periodicidad": "Tiene soporte finito y no se repite indefinidamente.",
                "paridad": "La forma es simétrica respecto al eje vertical; se cumple x(-t)=x(t).",
                "tipo_energetico": "Al estar limitada en el tiempo y tener amplitud acotada, su energía es finita.",
                "causalidad": "No es causal porque existen valores distintos de cero para t<0.",
            },
        ),
        SignalLevel(
            level=4,
            signal_id="rect_pulse_causal",
            title="Nivel 4: pulso rectangular causal",
            subtitle="Distinga entre soporte finito, causalidad y paridad.",
            equation=r"x(t)=3\,[u(t)-u(t-2)]",
            t_min=-2,
            t_max=4,
            y_min=-0.5,
            y_max=3.5,
            func=lambda t: 3 * (u(t) - u(t - 2)),
            answers={
                "dominio": "Tiempo continuo",
                "amplitud": "Análoga",
                "valores": "Real",
                "periodicidad": "Aperiódica",
                "paridad": "Ninguna",
                "tipo_energetico": "Energía",
                "causalidad": "Causal",
            },
            explanations={
                "dominio": "Aunque se grafique con una malla de puntos, el modelo matemático corresponde a tiempo continuo.",
                "amplitud": "La señal no se define como una señal digital cuantizada; se trata de una señal análoga idealizada.",
                "valores": "Su amplitud es real: toma los valores 0 y 3.",
                "periodicidad": "El pulso aparece una sola vez; no se repite con periodo T>0.",
                "paridad": "No presenta simetría par ni impar respecto al origen.",
                "tipo_energetico": "Tiene duración finita y amplitud acotada; por tanto, su energía es finita.",
                "causalidad": "Es cero para t<0, por lo que se clasifica como causal.",
            },
        ),
        SignalLevel(
            level=5,
            signal_id="ramp_causal",
            title="Nivel 5: rampa causal",
            subtitle="Reto final: identifique una señal que no es de energía ni de potencia.",
            equation=r"x(t)=t\,u(t)",
            t_min=-3,
            t_max=5,
            y_min=-0.5,
            y_max=5.5,
            func=lambda t: t * u(t),
            answers={
                "dominio": "Tiempo continuo",
                "amplitud": "Análoga",
                "valores": "Real",
                "periodicidad": "Aperiódica",
                "paridad": "Ninguna",
                "tipo_energetico": "Ninguna",
                "causalidad": "Causal",
            },
            explanations={
                "dominio": "La señal se define para una variable temporal continua t.",
                "amplitud": "El valor de la señal puede variar continuamente con t.",
                "valores": "La expresión t u(t) es real para todo t.",
                "periodicidad": "La rampa causal no repite su forma en intervalos regulares.",
                "paridad": "No es par ni impar porque el escalón unitario elimina la parte de tiempo negativo.",
                "tipo_energetico": "La energía es infinita y la potencia promedio también crece sin límite; por eso no es señal de energía ni de potencia.",
                "causalidad": "La señal es cero para t<0, por tanto es causal.",
            },
        ),
    ]


def get_level(level_number: int) -> SignalLevel:
    for level in levels():
        if level.level == level_number:
            return level
    raise ValueError(f"Nivel no encontrado: {level_number}")

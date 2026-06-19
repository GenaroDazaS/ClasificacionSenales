from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

DB_PATH = "senales_game.db"


def get_database_url() -> str:
    """Return database URL from Streamlit secrets/env or local SQLite fallback."""
    try:
        url = st.secrets.get("DATABASE_URL", None)
    except Exception:
        url = None
    url = url or os.environ.get("DATABASE_URL")
    if url:
        # SQLAlchemy expects postgresql+psycopg2 for many hosted Postgres URLs.
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+psycopg2://", 1)
        elif url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+psycopg2://", 1)
        return url
    return f"sqlite:///{DB_PATH}"


@st.cache_resource(show_spinner=False)
def get_engine() -> Engine:
    url = get_database_url()
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(url, future=True, pool_pre_ping=True, connect_args=connect_args)


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def init_db() -> None:
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            student_code TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL,
            group_name TEXT,
            created_at TEXT NOT NULL
        )
        """))
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_code TEXT NOT NULL,
            mode TEXT NOT NULL,
            competition_valid INTEGER NOT NULL DEFAULT 0,
            started_at TEXT NOT NULL,
            completed_at TEXT,
            status TEXT NOT NULL DEFAULT 'in_progress',
            total_levels INTEGER NOT NULL DEFAULT 5,
            levels_completed INTEGER NOT NULL DEFAULT 0,
            total_correct INTEGER NOT NULL DEFAULT 0,
            total_questions INTEGER NOT NULL DEFAULT 0,
            perfect_levels INTEGER NOT NULL DEFAULT 0,
            winner INTEGER NOT NULL DEFAULT 0,
            final_score REAL NOT NULL DEFAULT 0,
            metadata TEXT
        )
        """))
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS responses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            attempt_id INTEGER NOT NULL,
            student_code TEXT NOT NULL,
            level INTEGER NOT NULL,
            signal_id TEXT NOT NULL,
            submitted_at TEXT NOT NULL,
            answers TEXT NOT NULL,
            correct_answers TEXT NOT NULL,
            result_details TEXT NOT NULL,
            correct_count INTEGER NOT NULL,
            total_count INTEGER NOT NULL,
            is_perfect INTEGER NOT NULL,
            FOREIGN KEY(attempt_id) REFERENCES attempts(id)
        )
        """))
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS competition_settings (
            id INTEGER PRIMARY KEY,
            active INTEGER NOT NULL DEFAULT 0,
            competition_code TEXT NOT NULL DEFAULT 'SENALES',
            start_at TEXT,
            end_at TEXT,
            updated_at TEXT NOT NULL
        )
        """))
        existing = conn.execute(text("SELECT COUNT(*) FROM competition_settings WHERE id=1")).scalar_one()
        if existing == 0:
            conn.execute(text("""
            INSERT INTO competition_settings (id, active, competition_code, start_at, end_at, updated_at)
            VALUES (1, 0, 'SENALES', NULL, NULL, :updated_at)
            """), {"updated_at": now_iso()})


def upsert_student(name: str, student_code: str, email: str, group_name: str) -> None:
    engine = get_engine()
    with engine.begin() as conn:
        if engine.url.get_backend_name().startswith("sqlite"):
            conn.execute(text("""
            INSERT INTO students (name, student_code, email, group_name, created_at)
            VALUES (:name, :student_code, :email, :group_name, :created_at)
            ON CONFLICT(student_code) DO UPDATE SET
                name=excluded.name,
                email=excluded.email,
                group_name=excluded.group_name
            """), {
                "name": name.strip(), "student_code": student_code.strip(),
                "email": email.strip(), "group_name": group_name.strip(), "created_at": now_iso()
            })
        else:
            conn.execute(text("""
            INSERT INTO students (name, student_code, email, group_name, created_at)
            VALUES (:name, :student_code, :email, :group_name, :created_at)
            ON CONFLICT(student_code) DO UPDATE SET
                name=EXCLUDED.name,
                email=EXCLUDED.email,
                group_name=EXCLUDED.group_name
            """), {
                "name": name.strip(), "student_code": student_code.strip(),
                "email": email.strip(), "group_name": group_name.strip(), "created_at": now_iso()
            })


def get_student(student_code: str) -> Optional[Dict[str, Any]]:
    engine = get_engine()
    with engine.begin() as conn:
        row = conn.execute(text("SELECT * FROM students WHERE student_code=:code"), {"code": student_code}).mappings().first()
        return dict(row) if row else None


def get_competition_settings() -> Dict[str, Any]:
    engine = get_engine()
    with engine.begin() as conn:
        row = conn.execute(text("SELECT * FROM competition_settings WHERE id=1")).mappings().one()
        return dict(row)


def update_competition_settings(active: bool, competition_code: str, start_at: Optional[str], end_at: Optional[str]) -> None:
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(text("""
        UPDATE competition_settings
        SET active=:active, competition_code=:competition_code, start_at=:start_at, end_at=:end_at, updated_at=:updated_at
        WHERE id=1
        """), {
            "active": 1 if active else 0,
            "competition_code": competition_code.strip(),
            "start_at": start_at,
            "end_at": end_at,
            "updated_at": now_iso()
        })


def has_competition_attempt(student_code: str) -> bool:
    engine = get_engine()
    with engine.begin() as conn:
        count = conn.execute(text("""
        SELECT COUNT(*) FROM attempts
        WHERE student_code=:code AND mode='competencia' AND competition_valid=1
        """), {"code": student_code}).scalar_one()
        return count > 0


def create_attempt(student_code: str, mode: str, competition_valid: bool, metadata: Optional[Dict[str, Any]] = None) -> int:
    engine = get_engine()
    with engine.begin() as conn:
        result = conn.execute(text("""
        INSERT INTO attempts (student_code, mode, competition_valid, started_at, metadata)
        VALUES (:student_code, :mode, :competition_valid, :started_at, :metadata)
        """), {
            "student_code": student_code,
            "mode": mode,
            "competition_valid": 1 if competition_valid else 0,
            "started_at": now_iso(),
            "metadata": json.dumps(metadata or {}, ensure_ascii=False)
        })
        # SQLite supports lastrowid; Postgres through SQLAlchemy may not in this form.
        if result.lastrowid:
            return int(result.lastrowid)
        row = conn.execute(text("SELECT MAX(id) AS id FROM attempts WHERE student_code=:code"), {"code": student_code}).mappings().one()
        return int(row["id"])


def save_response(
    attempt_id: int,
    student_code: str,
    level: int,
    signal_id: str,
    answers: Dict[str, str],
    correct_answers: Dict[str, str],
    result_details: List[Dict[str, Any]],
    correct_count: int,
    total_count: int,
    is_perfect: bool,
) -> None:
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(text("""
        INSERT INTO responses (
            attempt_id, student_code, level, signal_id, submitted_at, answers,
            correct_answers, result_details, correct_count, total_count, is_perfect
        ) VALUES (
            :attempt_id, :student_code, :level, :signal_id, :submitted_at, :answers,
            :correct_answers, :result_details, :correct_count, :total_count, :is_perfect
        )
        """), {
            "attempt_id": attempt_id,
            "student_code": student_code,
            "level": level,
            "signal_id": signal_id,
            "submitted_at": now_iso(),
            "answers": json.dumps(answers, ensure_ascii=False),
            "correct_answers": json.dumps(correct_answers, ensure_ascii=False),
            "result_details": json.dumps(result_details, ensure_ascii=False),
            "correct_count": correct_count,
            "total_count": total_count,
            "is_perfect": 1 if is_perfect else 0,
        })
        recalc_attempt(conn, attempt_id)


def recalc_attempt(conn: Any, attempt_id: int) -> None:
    rows = conn.execute(text("""
    SELECT correct_count, total_count, is_perfect FROM responses WHERE attempt_id=:attempt_id
    """), {"attempt_id": attempt_id}).mappings().all()
    levels_completed = len(rows)
    total_correct = sum(int(r["correct_count"]) for r in rows)
    total_questions = sum(int(r["total_count"]) for r in rows)
    perfect_levels = sum(int(r["is_perfect"]) for r in rows)
    final_score = (100.0 * total_correct / total_questions) if total_questions else 0.0
    status = "completed" if levels_completed >= 5 else "in_progress"
    winner = 1 if levels_completed >= 5 and perfect_levels >= 5 else 0
    completed_at = now_iso() if status == "completed" else None
    conn.execute(text("""
    UPDATE attempts SET
        levels_completed=:levels_completed,
        total_correct=:total_correct,
        total_questions=:total_questions,
        perfect_levels=:perfect_levels,
        final_score=:final_score,
        status=:status,
        winner=:winner,
        completed_at=COALESCE(completed_at, :completed_at)
    WHERE id=:attempt_id
    """), {
        "levels_completed": levels_completed,
        "total_correct": total_correct,
        "total_questions": total_questions,
        "perfect_levels": perfect_levels,
        "final_score": final_score,
        "status": status,
        "winner": winner,
        "completed_at": completed_at,
        "attempt_id": attempt_id,
    })


def load_attempt_responses(attempt_id: int) -> pd.DataFrame:
    engine = get_engine()
    with engine.begin() as conn:
        return pd.read_sql(text("SELECT * FROM responses WHERE attempt_id=:attempt_id ORDER BY level"), conn, params={"attempt_id": attempt_id})


def load_attempt(attempt_id: int) -> Optional[Dict[str, Any]]:
    engine = get_engine()
    with engine.begin() as conn:
        row = conn.execute(text("SELECT * FROM attempts WHERE id=:id"), {"id": attempt_id}).mappings().first()
        return dict(row) if row else None


def load_dashboard_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    engine = get_engine()
    with engine.begin() as conn:
        attempts = pd.read_sql(text("""
        SELECT a.*, s.name, s.email, s.group_name
        FROM attempts a
        LEFT JOIN students s ON a.student_code=s.student_code
        ORDER BY a.started_at DESC
        """), conn)
        responses = pd.read_sql(text("""
        SELECT r.*, s.name, s.email, s.group_name, a.mode, a.competition_valid
        FROM responses r
        LEFT JOIN students s ON r.student_code=s.student_code
        LEFT JOIN attempts a ON r.attempt_id=a.id
        ORDER BY r.submitted_at DESC
        """), conn)
        return attempts, responses

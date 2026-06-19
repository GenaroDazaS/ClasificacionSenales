# Reto de Clasificación de Señales

Aplicación en Streamlit para una actividad tipo juego de clasificación de señales de tiempo continuo.

## Archivos principales

- `app.py`: aplicación principal.
- `game_data.py`: definición de niveles, señales, respuestas correctas y explicaciones.
- `db.py`: almacenamiento de estudiantes, intentos y respuestas.
- `ui.py`: estilos visuales, gráficas y componentes de retroalimentación.
- `requirements.txt`: dependencias para instalación y despliegue.
- `.streamlit/secrets.toml.example`: plantilla de secretos.

## Ejecución local

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Contraseña del profesor

Para pruebas locales, si no configura secretos, la contraseña predeterminada es:

```text
admin123
```

Se recomienda cambiarla usando `.streamlit/secrets.toml`:

```toml
TEACHER_PASSWORD = "mi_contrasena_segura"
```

## Base de datos

Por defecto usa SQLite local (`senales_game.db`). Para despliegue real, configure `DATABASE_URL` apuntando a PostgreSQL.

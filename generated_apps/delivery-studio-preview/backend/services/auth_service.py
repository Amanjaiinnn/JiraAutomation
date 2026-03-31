import hashlib
import secrets

from fastapi import HTTPException

from database import get_connection


def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def ensure_tables():
    connection = get_connection()
    with connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS app_users (
                    id SERIAL PRIMARY KEY,
                    name TEXT NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS auth_sessions (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER REFERENCES app_users(id) ON DELETE CASCADE,
                    session_token TEXT,
                    is_authenticated BOOLEAN NOT NULL DEFAULT FALSE,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS auth_audit_log (
                    id SERIAL PRIMARY KEY,
                    event_type TEXT NOT NULL,
                    email TEXT,
                    message TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            cursor.execute(
                """
                INSERT INTO auth_sessions (id, user_id, session_token, is_authenticated)
                VALUES (1, NULL, NULL, FALSE)
                ON CONFLICT (id) DO NOTHING
                """
            )
    connection.close()


def _log_event(event_type: str, email: str | None, message: str) -> None:
    connection = get_connection()
    with connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO auth_audit_log (event_type, email, message) VALUES (%s, %s, %s)",
                (event_type, email, message),
            )
    connection.close()


def register_user(data: dict):
    if not isinstance(data, dict):
        raise TypeError("Payload must be a dictionary")

    ensure_tables()
    name = str(data.get("name") or "").strip()
    email = str(data.get("email") or "").strip().lower()
    password = str(data.get("password") or "")

    if not name or not email or not password:
        raise HTTPException(status_code=400, detail="Name, email, and password are required.")

    connection = get_connection()
    try:
        with connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT id FROM app_users WHERE email = %s", (email,))
                if cursor.fetchone():
                    raise HTTPException(status_code=409, detail="An account with this email already exists.")
                cursor.execute(
                    """
                    INSERT INTO app_users (name, email, password_hash)
                    VALUES (%s, %s, %s)
                    RETURNING id, name, email
                    """,
                    (name, email, _hash_password(password)),
                )
                user = cursor.fetchone()
        _log_event("register", email, "Account created successfully")
        return {
            "message": "Account created successfully",
            "user": user,
            "is_authenticated": False,
        }
    finally:
        connection.close()


def login_user(data: dict):
    if not isinstance(data, dict):
        raise TypeError("Payload must be a dictionary")

    ensure_tables()
    email = str(data.get("email") or "").strip().lower()
    password = str(data.get("password") or "")

    if not email or not password:
        raise HTTPException(status_code=400, detail="Email and password are required.")

    connection = get_connection()
    try:
        with connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT id, name, email, password_hash FROM app_users WHERE email = %s",
                    (email,),
                )
                user = cursor.fetchone()
                if not user or user["password_hash"] != _hash_password(password):
                    raise HTTPException(status_code=401, detail="Invalid email or password.")
                token = secrets.token_hex(16)
                cursor.execute(
                    """
                    UPDATE auth_sessions
                    SET user_id = %s,
                        session_token = %s,
                        is_authenticated = TRUE,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = 1
                    """,
                    (user["id"], token),
                )
        _log_event("login", email, "Logged in successfully")
        return {
            "message": "Logged in successfully",
            "authentication_token": token,
            "user": {
                "id": user["id"],
                "name": user["name"],
                "email": user["email"],
            },
            "is_authenticated": True,
        }
    finally:
        connection.close()


def logout_user():
    ensure_tables()
    session = get_session()
    connection = get_connection()
    try:
        with connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE auth_sessions
                    SET user_id = NULL,
                        session_token = NULL,
                        is_authenticated = FALSE,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = 1
                    """
                )
        _log_event("logout", session["user"]["email"] if session["user"] else None, "Logged out successfully")
        return {
            "message": "Logged out successfully",
            "is_authenticated": False,
            "user": None,
        }
    finally:
        connection.close()


def get_session():
    ensure_tables()
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT s.is_authenticated, s.session_token, u.id, u.name, u.email
                FROM auth_sessions s
                LEFT JOIN app_users u ON u.id = s.user_id
                WHERE s.id = 1
                """
            )
            row = cursor.fetchone()
        user = None
        if row and row.get("id"):
            user = {"id": row["id"], "name": row["name"], "email": row["email"]}
        return {
            "is_authenticated": bool(row["is_authenticated"]) if row else False,
            "authentication_token": row["session_token"] if row else None,
            "user": user,
        }
    finally:
        connection.close()


def list_items():
    ensure_tables()
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, event_type, email, message, created_at
                FROM auth_audit_log
                ORDER BY id DESC
                """
            )
            return cursor.fetchall()
    finally:
        connection.close()


def create_register(data: dict):
    return register_user(data)


def create_login(data: dict):
    return login_user(data)

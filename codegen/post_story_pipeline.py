from __future__ import annotations

import json
import re
from typing import Any

from codegen.code_generator import normalize_project_config, run_project_unit_tests
from codegen.runtime_execution import RuntimeProjectManager


SAFE_NAME_PATTERN = re.compile(r"[^a-z0-9]+")
FIELD_HINTS = ["email", "password", "name", "status", "amount", "token", "role", "search", "query"]
MODULE_ALIASES = {
    "login": "auth",
    "log in": "auth",
    "log-in": "auth",
    "signin": "auth",
    "sign-in": "auth",
    "sign in": "auth",
    "signup": "auth",
    "sign up": "auth",
    "sign-up": "auth",
    "register": "auth",
    "registration": "auth",
    "authentication": "auth",
    "logout": "auth",
    "log out": "auth",
    "log-out": "auth",
    "payment": "payments",
    "invoice": "billing",
    "task": "tasks",
    "tasks": "tasks",
    "to-do": "tasks",
    "todo": "tasks",
    "work item": "tasks",
    "user": "users",
    "profile": "users",
}
_RUNTIME_MANAGER = RuntimeProjectManager()


def _safe_slug(value: str) -> str:
    return SAFE_NAME_PATTERN.sub("_", value.lower()).strip("_") or "module"


def _title_case(module: str) -> str:
    return "".join(part.capitalize() for part in module.split("_"))


def _display_title(module: str, route_name: str) -> str:
    normalized_module = module.replace("_", " ").strip() or "Item"
    singular_module = normalized_module[:-1] if normalized_module.endswith("s") else normalized_module
    tokens = [token for token in route_name.replace("-", "_").split("_") if token]
    if not tokens:
        return _title_case(module)

    action_map = {
        "create": "Create",
        "add": "Add",
        "new": "Create",
        "view": "View",
        "list": "View",
        "show": "View",
        "edit": "Edit",
        "update": "Update",
        "delete": "Delete",
        "remove": "Delete",
        "filter": "Filter",
        "search": "Search",
        "register": "Register",
        "login": "Login",
        "logout": "Logout",
        "sessions": "Sessions",
        "session": "Session",
        "submit": "Save",
    }

    first = tokens[0].lower()
    action = action_map.get(first, first.replace("_", " ").title())

    if module == "auth":
        if action in {"Register", "Login", "Logout", "Sessions", "Session"}:
            return action
        return f"{action} Auth"

    if action in {"View", "Filter", "Search", "List"}:
        noun = normalized_module.title()
    else:
        noun = singular_module.title()

    return f"{action} {noun}".strip()


def _extract_module_name(story: dict[str, Any]) -> str:
    title = str(story.get("title") or story.get("summary") or "module")
    lowered = title.lower()
    for keyword, module in MODULE_ALIASES.items():
        if keyword in lowered:
            return module
    words = [part for part in _safe_slug(title).split("_") if part]
    return "_".join(words[:2]) or "module"


def _story_text_parts(story: dict[str, Any], *keys: str) -> list[str]:
    parts: list[str] = []
    for key in keys:
        value = story.get(key)
        if isinstance(value, list):
            parts.extend(str(item).strip() for item in value if str(item).strip())
        elif value is not None:
            text = str(value).strip()
            if text:
                parts.append(text)
    return parts


def _extract_logic_steps(story: dict[str, Any]) -> list[str]:
    acceptance = story.get("acceptance_criteria")
    if isinstance(acceptance, list):
        steps = [str(item).strip() for item in acceptance if str(item).strip()]
        if steps:
            return steps
    elif acceptance is not None:
        text = str(acceptance).strip()
        if text:
            return [sentence.strip() for sentence in re.split(r"[.\n]+", text) if sentence.strip()]

    steps = _story_text_parts(story, "details", "description", "definition_of_done")
    if not steps:
        return ["System handles the requested workflow."]
    if len(steps) > 1:
        return steps
    return [sentence.strip() for sentence in re.split(r"[.\n]+", steps[0]) if sentence.strip()]


def _extract_fields(story: dict[str, Any]) -> list[str]:
    haystack = " ".join(_story_text_parts(story, "title", "summary", "details", "description", "acceptance_criteria", "definition_of_done")).lower()
    if any(keyword in haystack for keyword in ["login", "log in", "signin", "sign in"]):
        return ["email", "password"]
    if any(keyword in haystack for keyword in ["register", "registration", "signup", "sign up"]):
        return ["email", "password", "name"]
    if "task" in haystack:
        fields = ["title", "description"]
        if any(keyword in haystack for keyword in ["due date", "deadline", "due-date"]):
            fields.append("due_date")
        if "priority" in haystack:
            fields.append("priority")
        if "status" in haystack:
            fields.append("status")
        if any(keyword in haystack for keyword in ["assign", "assignee", "owner"]):
            fields.append("assignee")
        return fields
    found = [field for field in FIELD_HINTS if field in haystack]
    return found or ["title", "details"]


def _extract_ui_reference(story: dict[str, Any]) -> dict[str, str]:
    candidate = story.get("ui_reference")
    if not isinstance(candidate, dict):
        return {"text": "", "image_name": ""}
    return {
        "text": str(candidate.get("text") or "").strip(),
        "image_name": str(candidate.get("image_name") or "").strip(),
    }


def _extract_ui_guidance(story: dict[str, Any]) -> str:
    reference = _extract_ui_reference(story)
    parts: list[str] = []
    if reference["text"]:
        parts.append(reference["text"])
    if reference["image_name"]:
        parts.append(f"Use the attached screenshot reference ({reference['image_name']}) as visual direction.")
    return " ".join(parts).strip()


def build_language_neutral_spec(story: dict[str, Any]) -> dict[str, Any]:
    module = _extract_module_name(story)
    inputs = _extract_fields(story)
    logic_steps = _extract_logic_steps(story)
    ui_guidance = _extract_ui_guidance(story)

    outputs = []
    flattened = " ".join(logic_steps).lower()
    if "token" in flattened:
        outputs.append("authentication_token")
    if "error" in flattened or "invalid" in flattened:
        outputs.append("error_message")
    outputs.append("result")

    dependencies = ["data_store"]
    if "validate" in flattened:
        dependencies.append("validation_rules")

    return {
        "module": module,
        "functions": [
            {
                "name": f"{module}_workflow",
                "inputs": inputs,
                "outputs": outputs,
                "logic_steps": logic_steps,
                "dependencies": dependencies,
            }
        ],
        "ui_guidance": ui_guidance,
    }


def build_application_architecture(specifications: list[dict[str, Any]], selected_language: str, existing_modules: list[str]) -> dict[str, Any]:
    modules = sorted({*existing_modules, *(spec["module"] for spec in specifications)})
    endpoints = []
    services = []
    data_models = []
    frontend_pages = []
    frontend_components = []

    for spec in specifications:
        module = spec["module"]
        service_name = f"{module}_service"
        page_name = f"{_title_case(module)}Page"
        component_name = f"{_title_case(module)}Form"
        if module == "auth":
            endpoints.append({"method": "POST", "path": "/auth/login"})
            endpoints.append({"method": "GET", "path": "/auth/sessions"})
        else:
            endpoints.append({"method": "GET", "path": f"/{module}"})
            endpoints.append({"method": "POST", "path": f"/{module}"})
        services.append(service_name)
        data_models.append(f"{module}_record")
        frontend_pages.append(page_name)
        frontend_components.append(component_name)

    return {
        "selected_language": selected_language,
        "modules": modules,
        "api_endpoints": endpoints,
        "services": sorted(set(services)),
        "data_models": sorted(set(data_models)),
        "frontend_pages": sorted(set(frontend_pages)),
        "frontend_components": sorted(set(frontend_components)),
        "project_structure": {
            "backend": ["main.py", "routers/", "services/", "models/", "database.py"],
            "frontend": ["package.json", "vite.config.js", "src/App.jsx", "src/pages/", "src/components/", "src/api/"],
            "tests": ["unit/", "integration/"],
            "docs": ["manual_tests.md"],
        },
    }


def _read_modules_registry(existing_files: dict[str, str]) -> list[str]:
    raw = existing_files.get("modules.json")
    if not raw:
        return []
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return []
    return [str(item) for item in payload.get("modules", []) if str(item).strip()]


def _read_story_registry(existing_files: dict[str, str]) -> dict[str, list[dict[str, Any]]]:
    raw = existing_files.get("story_registry.json")
    if not raw:
        return {}
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return {}

    modules = payload.get("modules", {})
    if not isinstance(modules, dict):
        return {}

    registry: dict[str, list[dict[str, Any]]] = {}
    for module, workflows in modules.items():
        if not isinstance(workflows, list):
            continue
        registry[str(module)] = [item for item in workflows if isinstance(item, dict)]
    return registry


def _module_list_path(module: str) -> str:
    return "/auth/sessions" if module == "auth" else f"/{module}"


def _derive_route_name(story: dict[str, Any], module: str) -> str:
    haystack = " ".join(_story_text_parts(story, "title", "summary", "details", "description", "acceptance_criteria", "definition_of_done")).lower()
    if module == "auth":
        if any(keyword in haystack for keyword in ["login", "log in", "signin", "sign in"]):
            return "login"
        if any(keyword in haystack for keyword in ["register", "registration", "signup", "sign up"]):
            return "register"
        if any(keyword in haystack for keyword in ["logout", "log out", "signout", "sign out"]):
            return "logout"
        if "session" in haystack:
            return "sessions"

    title = str(story.get("title") or story.get("summary") or module)
    tokens = [token for token in _safe_slug(title).split("_") if token]
    stop_words = {
        "a",
        "an",
        "and",
        "allow",
        "app",
        "application",
        "as",
        "be",
        "can",
        "flow",
        "for",
        "i",
        "manage",
        "module",
        "page",
        "screen",
        "should",
        "so",
        "story",
        "system",
        "that",
        "the",
        "to",
        "user",
        "users",
        "want",
        "with",
    }
    stop_words.update(module.split("_"))
    filtered = [token for token in tokens if token not in stop_words]
    route_tokens = filtered[:3] or ["submit"]
    return "-".join(route_tokens)


def _derive_story_key(story: dict[str, Any], module: str, route_name: str) -> str:
    if module == "auth":
        return route_name.replace("-", "_")

    title = str(story.get("title") or story.get("summary") or module)
    tokens = [token for token in _safe_slug(title).split("_") if token]
    stop_words = {
        "a",
        "an",
        "and",
        "allow",
        "app",
        "application",
        "as",
        "be",
        "can",
        "flow",
        "for",
        "i",
        "module",
        "page",
        "screen",
        "should",
        "story",
        "system",
        "that",
        "the",
        "to",
        "want",
        "with",
    }
    stop_words.update(module.split("_"))
    filtered = [token for token in tokens if token not in stop_words]
    return "_".join(filtered[:2] or [module])


def _build_story_workflow(
    story: dict[str, Any],
    specification: dict[str, Any],
    existing_workflows: list[dict[str, Any]],
) -> dict[str, Any]:
    title = str(story.get("title") or story.get("summary") or specification["module"])
    current = next(
        (
            workflow
            for workflow in existing_workflows
            if workflow.get("story_title") == title or workflow.get("story_key") == _safe_slug(title)
        ),
        None,
    )

    current_story_key = current.get("story_key") if current else None
    route_name = current.get("route_name") if current else _derive_route_name(story, specification["module"])
    used_routes = {
        str(workflow.get("route_name"))
        for workflow in existing_workflows
        if workflow.get("story_key") != current_story_key and workflow.get("route_name")
    }
    base_route = route_name or "submit"
    suffix = 2
    while route_name in used_routes:
        route_name = f"{base_route}-{suffix}"
        suffix += 1

    story_key = current.get("story_key") if current else _derive_story_key(story, specification["module"], route_name)
    used_keys = {
        str(workflow.get("story_key"))
        for workflow in existing_workflows
        if workflow.get("story_title") != title and workflow.get("story_key")
    }
    base_key = story_key or specification["module"]
    key_suffix = 2
    while story_key in used_keys:
        story_key = f"{base_key}_{key_suffix}"
        key_suffix += 1

    return {
        "story_key": story_key,
        "story_title": title,
        "display_title": _display_title(specification["module"], route_name),
        "module": specification["module"],
        "route_name": route_name,
        "fields": specification["functions"][0]["inputs"],
        "logic_steps": specification["functions"][0]["logic_steps"],
        "outputs": specification["functions"][0]["outputs"],
        "ui_guidance": specification.get("ui_guidance", ""),
    }


def _upsert_story_registry(
    registry: dict[str, list[dict[str, Any]]],
    workflow: dict[str, Any],
) -> dict[str, list[dict[str, Any]]]:
    updated = {module: [dict(item) for item in workflows] for module, workflows in registry.items()}
    module = workflow["module"]
    existing = updated.setdefault(module, [])

    for index, item in enumerate(existing):
        if item.get("story_key") == workflow["story_key"]:
            existing[index] = workflow
            break
    else:
        existing.append(workflow)

    return updated


def _registry_stories(story_registry: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    stories: list[dict[str, Any]] = []
    for workflows in story_registry.values():
        for workflow in workflows:
            stories.append(
                {
                    "title": workflow.get("story_title", ""),
                    "summary": workflow.get("story_title", ""),
                    "acceptance_criteria": workflow.get("logic_steps", []),
                }
            )
    return stories


def _python_model_name(story_key: str) -> str:
    return f"{_title_case(story_key)}Request"


def _python_create_function_name(story_key: str) -> str:
    return f"create_{story_key}"


def _workflow_submit_path(module: str, workflow: dict[str, Any]) -> str:
    route_name = workflow["route_name"]
    if module == "auth":
        return f"/auth/{route_name}"
    return f"/{module}/{route_name}"


def _render_python_backend_main(modules: list[str]) -> str:
    imports = "\n".join(f"from routers import {module}_router" for module in modules)
    includes = "\n".join(f"app.include_router({module}_router.router)" for module in modules)
    return f"""from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

{imports}

app = FastAPI(title="Generated Story App")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

{includes}


@app.get("/health")
def health():
    return {{"status": "ok"}}
"""


def _render_python_database() -> str:
    return """import os
from pathlib import Path

import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv


load_dotenv(Path(__file__).resolve().parent / ".env")


def get_database_url() -> str:
    return os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/generated_story_app")


def get_connection():
    return psycopg2.connect(get_database_url(), cursor_factory=RealDictCursor)
"""


def _render_python_service(module: str, workflows: list[dict[str, Any]]) -> str:
    handlers = []
    for workflow in workflows:
        function_name = _python_create_function_name(workflow["story_key"])
        handlers.append(
            f"""
def {function_name}(data: dict):
    return _create_record(
        workflow="{workflow["route_name"]}",
        data=data,
        expected_fields={workflow["fields"]!r},
        success_message="{workflow.get("display_title") or workflow["story_title"]} completed",
    )
""".strip()
        )

    return f"""import json

from database import get_connection


TABLE_NAME = "{module}_records"


def ensure_table():
    connection = get_connection()
    with connection:
        with connection.cursor() as cursor:
            cursor.execute(
                \"\"\"
                CREATE TABLE IF NOT EXISTS {module}_records (
                    id SERIAL PRIMARY KEY,
                    workflow TEXT NOT NULL,
                    payload JSONB NOT NULL,
                    status TEXT NOT NULL
                )
                \"\"\"
            )
    connection.close()


def list_items(workflow: str | None = None):
    ensure_table()
    connection = get_connection()
    with connection.cursor() as cursor:
        if workflow:
            cursor.execute(
                "SELECT id, workflow, payload, status FROM {module}_records WHERE workflow = %s ORDER BY id DESC",
                (workflow,),
            )
        else:
            cursor.execute(
                "SELECT id, workflow, payload, status FROM {module}_records ORDER BY id DESC"
            )
        rows = cursor.fetchall()
    connection.close()
    return rows


def _create_record(workflow: str, data: dict, expected_fields: list[str], success_message: str):
    if not isinstance(data, dict):
        raise TypeError("Payload must be a dictionary")

    ensure_table()
    connection = get_connection()
    with connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO {module}_records (workflow, payload, status) VALUES (%s, %s::jsonb, %s)",
                (workflow, json.dumps(data), "created"),
            )
    connection.close()
    return {{
        "message": success_message,
        "workflow": workflow,
        "fields": expected_fields,
        "data": data,
    }}


{chr(10).join(handlers)}
"""


def _render_python_auth_service() -> str:
    return '''import hashlib
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
'''


def _render_python_auth_router() -> str:
    return """from fastapi import APIRouter
from pydantic import BaseModel, EmailStr

from services import auth_service


class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("")
def list_auth():
    return auth_service.list_items()


@router.get("/sessions")
def list_sessions():
    return auth_service.list_items()


@router.get("/session")
def get_session():
    return auth_service.get_session()


@router.post("/register")
def register(payload: RegisterRequest):
    return auth_service.register_user(payload.model_dump())


@router.post("/login")
def login(payload: LoginRequest):
    return auth_service.login_user(payload.model_dump())


@router.post("/logout")
def logout():
    return auth_service.logout_user()
"""


def _render_python_router(module: str, workflows: list[dict[str, Any]]) -> str:
    model_blocks = []
    route_blocks = [
        f"""router = APIRouter(prefix="/{module}", tags=["{module}"])\n\n\n@router.get("")\ndef list_{module}():\n    return {module}_service.list_items()"""
    ]

    if module == "auth":
        route_blocks.append(
            f"""
@router.get("/sessions")
def list_sessions():
    return {module}_service.list_items()
""".strip()
        )

    for index, workflow in enumerate(workflows):
        model_name = _python_model_name(workflow["story_key"])
        create_name = _python_create_function_name(workflow["story_key"])
        fields = workflow["fields"] or ["title", "details"]
        model_blocks.append(
            f"""class {model_name}(BaseModel):
{chr(10).join(f"    {field}: str" for field in fields)}
""".strip()
        )

        submit_path = _workflow_submit_path(module, workflow).replace(f"/{module}", "", 1)
        handler_name = f"submit_{workflow['story_key']}"
        route_blocks.append(
            f"""
@router.post("{submit_path}")
def {handler_name}(payload: {model_name}):
    response = {module}_service.{create_name}(payload.model_dump())
    {"response['authentication_token'] = 'demo-token'" if module == "auth" else ""}
    return response
""".strip()
        )

        if module != "auth" and index == 0:
            route_blocks.append(
                f"""
@router.post("")
def create_{module}(payload: {model_name}):
    return {module}_service.{create_name}(payload.model_dump())
""".strip()
            )

    return f"""from fastapi import APIRouter
from pydantic import BaseModel

from services import {module}_service


{chr(10).join(model_blocks)}


{chr(10).join(route_blocks)}
"""


def _render_frontend_package_json() -> str:
    return json.dumps(
        {
            "name": "generated-story-frontend",
            "private": True,
            "version": "0.0.1",
            "scripts": {
                "dev": "vite --host 0.0.0.0 --port 5174",
                "build": "vite build",
            },
            "dependencies": {
                "react": "^18.3.1",
                "react-dom": "^18.3.1",
            },
            "devDependencies": {
                "@vitejs/plugin-react": "^4.3.2",
                "vite": "^5.4.8",
            },
        },
        indent=2,
    )


def _render_frontend_vite_config() -> str:
    return """import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: 5174,
  },
});
"""


def _render_frontend_main() -> str:
    return """import React from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App";
import "./styles.css";

createRoot(document.getElementById("root")).render(<App />);
"""


def _render_frontend_styles() -> str:
    return """:root {
  font-family: "Segoe UI", sans-serif;
  color: #14213d;
  background:
    radial-gradient(circle at top left, rgba(251, 191, 36, 0.18), transparent 28%),
    radial-gradient(circle at bottom right, rgba(37, 99, 235, 0.18), transparent 30%),
    #f5f7fb;
}

body {
  margin: 0;
  color: #14213d;
}

.shell {
  max-width: 1180px;
  margin: 0 auto;
  padding: 32px 20px 48px;
}

.app-topbar {
  display: flex;
  justify-content: space-between;
  gap: 20px;
  align-items: flex-start;
  padding: 28px;
  border-radius: 28px;
  background: linear-gradient(135deg, #0f172a, #1d4ed8 55%, #38bdf8);
  color: #fff;
  box-shadow: 0 24px 48px rgba(15, 23, 42, 0.22);
  margin-bottom: 22px;
}

.app-topbar h1 {
  margin: 0 0 10px;
  font-size: 2rem;
}

.app-topbar p {
  margin: 0;
  max-width: 720px;
  line-height: 1.6;
  color: rgba(255, 255, 255, 0.82);
}

.app-nav {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 22px;
}

.app-nav button {
  border: none;
  border-radius: 999px;
  padding: 12px 18px;
  font-weight: 700;
  cursor: pointer;
  background: rgba(255, 255, 255, 0.14);
  color: #fff;
}

.app-nav button.active {
  background: linear-gradient(135deg, #f59e0b, #f97316);
}

.page {
  min-height: calc(100vh - 64px);
}

.auth-shell {
  display: grid;
  gap: 24px;
}

.auth-header {
  display: flex;
  justify-content: space-between;
  gap: 20px;
  align-items: flex-start;
  padding: 28px;
  border-radius: 28px;
  background: linear-gradient(135deg, #0f172a, #1d4ed8 55%, #38bdf8);
  color: #fff;
  box-shadow: 0 24px 48px rgba(15, 23, 42, 0.22);
}

.auth-header h1 {
  margin: 8px 0 10px;
  font-size: 2rem;
}

.hero-copy,
.panel-copy,
.muted {
  color: #5b6b85;
}

.hero-copy {
  max-width: 680px;
  color: rgba(255, 255, 255, 0.82);
  line-height: 1.6;
}

.auth-nav {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.nav-link,
.logout-button,
.auth-form button {
  border: none;
  border-radius: 999px;
  padding: 12px 18px;
  font-weight: 700;
  cursor: pointer;
}

.nav-link {
  background: rgba(255, 255, 255, 0.14);
  color: #fff;
}

.nav-link.active,
.auth-form button,
.logout-button {
  background: linear-gradient(135deg, #f59e0b, #f97316);
  color: #fff;
}

.feedback-banner {
  padding: 14px 18px;
  border-radius: 18px;
  font-weight: 600;
}

.feedback-banner.success {
  background: #dcfce7;
  color: #166534;
}

.feedback-banner.error {
  background: #fee2e2;
  color: #991b1b;
}

.auth-content {
  display: grid;
  grid-template-columns: minmax(0, 1.3fr) minmax(280px, 0.7fr);
  gap: 20px;
}

.auth-content-single {
  grid-template-columns: 1fr;
}

.auth-panel {
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid rgba(148, 163, 184, 0.2);
  border-radius: 24px;
  padding: 24px;
  box-shadow: 0 18px 40px rgba(15, 23, 42, 0.08);
}

.auth-panel-primary h2,
.auth-panel-secondary h3 {
  margin-top: 0;
}

.auth-form {
  display: grid;
  gap: 14px;
  margin-top: 18px;
}

.auth-form label span {
  display: block;
  font-size: 0.85rem;
  font-weight: 700;
  margin-bottom: 8px;
}

input {
  width: 100%;
  border: 1px solid #cbd5e1;
  border-radius: 14px;
  padding: 12px 14px;
  background: #fff;
}

textarea,
select {
  width: 100%;
  border: 1px solid #cbd5e1;
  border-radius: 14px;
  padding: 12px 14px;
  background: #fff;
}

.session-card {
  border: 1px solid #dbeafe;
  border-radius: 18px;
  background: linear-gradient(180deg, #ffffff, #eff6ff);
  padding: 16px;
}

.module-shell {
  display: grid;
  gap: 22px;
}

.module-hero {
  padding: 24px 26px;
  border-radius: 24px;
  background: linear-gradient(135deg, rgba(15, 23, 42, 0.95), rgba(29, 78, 216, 0.88));
  color: #fff;
  box-shadow: 0 24px 48px rgba(15, 23, 42, 0.16);
}

.module-hero h2 {
  margin: 0 0 10px;
  font-size: 1.8rem;
}

.module-hero p {
  margin: 0;
  max-width: 720px;
  line-height: 1.6;
  color: rgba(255, 255, 255, 0.82);
}

.module-layout {
  display: grid;
  grid-template-columns: minmax(0, 1.05fr) minmax(320px, 0.95fr);
  gap: 20px;
}

.module-panel {
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid rgba(148, 163, 184, 0.2);
  border-radius: 24px;
  padding: 22px;
  box-shadow: 0 18px 40px rgba(15, 23, 42, 0.08);
}

.module-panel h3,
.module-panel h4 {
  margin-top: 0;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.form-grid .field-span-full {
  grid-column: 1 / -1;
}

.primary-button,
.ghost-button {
  border: none;
  border-radius: 999px;
  padding: 12px 18px;
  font-weight: 700;
  cursor: pointer;
}

.primary-button {
  background: linear-gradient(135deg, #f59e0b, #f97316);
  color: #fff;
}

.ghost-button {
  background: #eff6ff;
  color: #1d4ed8;
}

.button-row {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  margin-top: 18px;
}

.session-strip {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 22px;
  padding: 16px 20px;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid rgba(148, 163, 184, 0.2);
  box-shadow: 0 12px 28px rgba(15, 23, 42, 0.08);
}

.session-strip p {
  margin: 6px 0 0;
}

.inline-action {
  border: none;
  background: transparent;
  color: #1d4ed8;
  font-weight: 700;
  padding: 0;
  cursor: pointer;
}

.record-stack {
  display: grid;
  gap: 12px;
  margin-top: 16px;
}

.record-card {
  border: 1px solid #dbeafe;
  border-radius: 18px;
  padding: 16px;
  background: linear-gradient(180deg, #ffffff, #eff6ff);
}

.record-card p,
.record-card li {
  margin: 0;
  color: #334155;
}

.record-card ul {
  margin: 10px 0 0;
  padding-left: 18px;
}

.status-badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  border-radius: 999px;
  padding: 8px 12px;
  font-size: 0.8rem;
  font-weight: 700;
  background: #dbeafe;
  color: #1d4ed8;
}

@media (max-width: 960px) {
  .app-topbar,
  .auth-header,
  .auth-content,
  .module-layout,
  .form-grid {
    grid-template-columns: 1fr;
    flex-direction: column;
  }
}
"""


def _render_frontend_api_config() -> str:
    return 'export const API_BASE = "http://localhost:8001";\n'


def _render_frontend_api_client() -> str:
    return """import { API_BASE } from "../config/api";

export async function apiGet(path) {
  const response = await fetch(`${API_BASE}${path}`);
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.detail || data.message || "Request failed");
  }
  return data;
}

export async function apiPost(path, payload) {
  const response = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.detail || data.message || "Request failed");
  }
  return data;
}
"""


def _render_frontend_app(modules: list[str]) -> str:
    imports = "\n".join(f'import {{ {_title_case(module)}Page }} from "./pages/{_title_case(module)}Page";' for module in modules)
    page_map = ",\n  ".join(f'"{module}": {_title_case(module)}Page' for module in modules)
    content_modules = [module for module in modules if module != "auth"]
    initial = content_modules[0] if content_modules else (modules[0] if modules else "")
    buttons = "\n            ".join(
        f'<button key="{module}" className={{activePage === "{module}" ? "active" : ""}} onClick={{() => setActivePage("{module}")}}>{_title_case(module)}</button>'
        for module in content_modules
    )
    return f"""import React, {{ useEffect, useMemo, useState }} from "react";
{imports}
import {{ apiGet, apiPost }} from "./api/client";

const pageMap = {{
  {page_map}
}};

export function App() {{
  const [activePage, setActivePage] = useState("{initial}");
  const [session, setSession] = useState({{ is_authenticated: false, user: null }});
  const [sessionLoading, setSessionLoading] = useState({str(bool("auth" in modules)).lower()});
  const [sessionError, setSessionError] = useState("");
  const hasAuth = {str(bool("auth" in modules)).lower()};
  const contentModules = {json.dumps(content_modules)};

  const refreshSession = async () => {{
    if (!hasAuth) {{
      return;
    }}
    setSessionLoading(true);
    setSessionError("");
    try {{
      const data = await apiGet("/auth/session");
      setSession(data || {{ is_authenticated: false, user: null }});
    }} catch (error) {{
      setSessionError(error.message);
      setSession({{ is_authenticated: false, user: null }});
    }} finally {{
      setSessionLoading(false);
    }}
  }};

  const applyAuthenticatedSession = (nextSession) => {{
    setSession(nextSession || {{ is_authenticated: true, user: null }});
    setSessionError("");
    setSessionLoading(false);
    if (contentModules.length && !contentModules.includes(activePage)) {{
      setActivePage(contentModules[0]);
    }}
  }};

  const applyLoggedOutState = () => {{
    setSession({{ is_authenticated: false, user: null }});
    setSessionLoading(false);
  }};

  useEffect(() => {{
    refreshSession();
  }}, []);

  useEffect(() => {{
    if (!contentModules.length) {{
      setActivePage(hasAuth ? "auth" : "");
      return;
    }}
    if (!contentModules.includes(activePage)) {{
      setActivePage(contentModules[0]);
    }}
  }}, [activePage, hasAuth]);

  const ActivePage = useMemo(() => pageMap[activePage], [activePage]);

  const handleLogout = async () => {{
    try {{
      await apiPost("/auth/logout", {{}});
    }} catch (_error) {{
      // Keep the UI gated even if the backend session is already invalid.
    }}
    applyLoggedOutState();
    setActivePage(contentModules[0] || "auth");
  }};

  if (hasAuth && sessionLoading) {{
    return (
      <div className="shell">
        <section className="auth-panel auth-panel-primary">
          <h2>Checking your session</h2>
          <p className="panel-copy">Protected content stays hidden until authentication is confirmed.</p>
        </section>
      </div>
    );
  }}

  if (hasAuth && !session?.is_authenticated) {{
    const AuthPage = pageMap.auth;
    return AuthPage ? <AuthPage onAuthenticated={{applyAuthenticatedSession}} onLoggedOut={{applyLoggedOutState}} /> : null;
  }}

  if (hasAuth && !contentModules.length) {{
    const AuthPage = pageMap.auth;
    return AuthPage ? <AuthPage onAuthenticated={{applyAuthenticatedSession}} onLoggedOut={{applyLoggedOutState}} /> : null;
  }}

  return (
    <div className="shell">
      <header className="app-topbar">
        <div>
          <h1>Generated Story Application</h1>
          <p>Track activity, review recent updates, and move through the main workflows from one place.</p>
        </div>
      </header>
      {{hasAuth ? (
        <section className="session-strip">
          <div>
            <strong>{{session?.user?.name || "Authenticated user"}}</strong>
            <p className="muted">{{sessionError || session?.user?.email || "Your protected workspace is unlocked."}}</p>
          </div>
          <button type="button" className="ghost-button" onClick={{handleLogout}}>Logout</button>
        </section>
      ) : null}}
      {{contentModules.length ? (
        <nav className="app-nav">
          {buttons}
        </nav>
      ) : null}}
      <div className="page">
        {{ActivePage ? <ActivePage /> : <p>No modules generated yet.</p>}}
      </div>
    </div>
  );
}}
"""


def _render_frontend_auth_page(workflows: list[dict[str, Any]]) -> str:
    workflow_titles = [workflow.get("display_title") or workflow["story_title"] for workflow in workflows if workflow.get("story_title")]
    template = """import React, { useEffect, useMemo, useState } from "react";
import { apiGet, apiPost } from "../api/client";

const workflowTitles = __WORKFLOW_TITLES__;

const ROUTES = {
  register: "#/register",
  login: "#/login",
  dashboard: "#/dashboard",
};

const getCurrentView = () => {
  const hash = window.location.hash || ROUTES.register;
  if (hash === ROUTES.login) return "login";
  if (hash === ROUTES.dashboard) return "dashboard";
  return "register";
};

const emptyRegisterForm = { name: "", email: "", password: "" };
const emptyLoginForm = { email: "", password: "" };

export function AuthPage({ onAuthenticated = () => {}, onLoggedOut = () => {} }) {
  const [view, setView] = useState(getCurrentView);
  const [registerForm, setRegisterForm] = useState(emptyRegisterForm);
  const [loginForm, setLoginForm] = useState(emptyLoginForm);
  const [session, setSession] = useState({ is_authenticated: false, user: null });
  const [banner, setBanner] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const applyView = (nextView) => {
    window.location.hash = ROUTES[nextView] || ROUTES.register;
    setView(nextView);
  };

  const refreshSession = async () => {
    const sessionData = await apiGet("/auth/session");
    setSession(sessionData || { is_authenticated: false, user: null });
    if (sessionData?.is_authenticated && getCurrentView() !== "dashboard") {
      applyView("dashboard");
    }
    return sessionData;
  };

  useEffect(() => {
    const syncFromHash = () => setView(getCurrentView());
    window.addEventListener("hashchange", syncFromHash);
    refreshSession().catch((requestError) => setError(requestError.message));
    syncFromHash();
    return () => window.removeEventListener("hashchange", syncFromHash);
  }, []);

  const welcomeTitle = useMemo(() => {
    if (session?.user?.name) return `Welcome back, ${session.user.name}`;
    return "Authentication workspace";
  }, [session]);

  const handleRegister = async (event) => {
    event.preventDefault();
    setLoading(true);
    setError("");
    setBanner(null);
    try {
      const data = await apiPost("/auth/register", registerForm);
      setBanner(data.message || "Account created successfully");
      setRegisterForm(emptyRegisterForm);
      await refreshSession();
      applyView("login");
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setLoading(false);
    }
  };

  const handleLogin = async (event) => {
    event.preventDefault();
    setLoading(true);
    setError("");
    setBanner(null);
    try {
      const data = await apiPost("/auth/login", loginForm);
      setBanner(data.message || "Logged in successfully");
      setLoginForm(emptyLoginForm);
      const sessionData = await refreshSession();
      if (sessionData?.is_authenticated) {
        onAuthenticated(sessionData);
      }
      applyView("dashboard");
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = async () => {
    setLoading(true);
    setError("");
    setBanner(null);
    try {
      const data = await apiPost("/auth/logout", {});
      setBanner(data.message || "Logged out successfully");
      setSession({ is_authenticated: false, user: null });
      applyView("login");
      onLoggedOut();
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-shell">
      <header className="auth-header">
        <div>
          <h1>{welcomeTitle}</h1>
          <p className="hero-copy">Sign in first to unlock the application. Protected pages and navigation stay hidden until the session is authenticated.</p>
          {workflowTitles.length ? (
            <div className="button-row" style={{ marginTop: 12 }}>
              {workflowTitles.map((title) => (
                <span key={title} className="status-badge">{title}</span>
              ))}
            </div>
          ) : null}
        </div>
      </header>

      {banner ? <div className="feedback-banner success">{banner}</div> : null}
      {error ? <div className="feedback-banner error">{error}</div> : null}

      <section className="auth-content auth-content-single">
        <article className="auth-panel auth-panel-primary">
          {view === "register" ? (
            <>
              <h2>Create your account</h2>
              <p className="panel-copy">Register with your name, email, and password. After success, you will be guided to the login page.</p>
              <form className="auth-form" onSubmit={handleRegister}>
                <label>
                  <span>Full Name</span>
                  <input value={registerForm.name} onChange={(event) => setRegisterForm((previous) => ({ ...previous, name: event.target.value }))} placeholder="Aman Verma" />
                </label>
                <label>
                  <span>Email</span>
                  <input type="email" value={registerForm.email} onChange={(event) => setRegisterForm((previous) => ({ ...previous, email: event.target.value }))} placeholder="aman@example.com" />
                </label>
                <label>
                  <span>Password</span>
                  <input type="password" value={registerForm.password} onChange={(event) => setRegisterForm((previous) => ({ ...previous, password: event.target.value }))} placeholder="Choose a strong password" />
                </label>
                <button type="submit" disabled={loading}>{loading ? "Creating account..." : "Create Account"}</button>
              </form>
              <p className="muted">Already have an account? <button type="button" className="inline-action" onClick={() => applyView("login")}>Go to login</button></p>
            </>
          ) : null}

          {view === "login" ? (
            <>
              <h2>Sign in to continue</h2>
              <p className="panel-copy">Use the credentials stored in PostgreSQL to create an authenticated session.</p>
              <form className="auth-form" onSubmit={handleLogin}>
                <label>
                  <span>Email</span>
                  <input type="email" value={loginForm.email} onChange={(event) => setLoginForm((previous) => ({ ...previous, email: event.target.value }))} placeholder="aman@example.com" />
                </label>
                <label>
                  <span>Password</span>
                  <input type="password" value={loginForm.password} onChange={(event) => setLoginForm((previous) => ({ ...previous, password: event.target.value }))} placeholder="Enter your password" />
                </label>
                <button type="submit" disabled={loading}>{loading ? "Signing in..." : "Login"}</button>
              </form>
              <p className="muted">Need an account first? <button type="button" className="inline-action" onClick={() => applyView("register")}>Create one</button></p>
            </>
          ) : null}

          {view === "dashboard" ? (
            <>
              <h2>Authenticated dashboard</h2>
              <p className="panel-copy">Logout is available only while the session is active, and the header updates immediately after sign in or sign out.</p>
              <div className="session-card">
                <p><strong>Status:</strong> {session?.is_authenticated ? "Logged in" : "Logged out"}</p>
                <p><strong>Name:</strong> {session?.user?.name || "Guest"}</p>
                <p><strong>Email:</strong> {session?.user?.email || "Not available"}</p>
              </div>
              <div className="button-row">
                <button type="button" className="logout-button" onClick={handleLogout} disabled={loading}>
                  {loading ? "Signing out..." : "Logout"}
                </button>
              </div>
            </>
          ) : null}
        </article>
      </section>
    </div>
  );
}
"""
    return template.replace("__WORKFLOW_TITLES__", json.dumps(workflow_titles, indent=2))


def _render_frontend_page(module: str, workflows: list[dict[str, Any]]) -> str:
    if module == "auth":
        return _render_frontend_auth_page(workflows)

    title = _title_case(module)
    workflow_data = [
        {
            "storyKey": workflow["story_key"],
            "title": workflow.get("display_title") or workflow["story_title"],
            "fields": workflow["fields"] or ["title", "details"],
            "submitPath": _workflow_submit_path(module, workflow),
            "listPath": _module_list_path(module),
            "routeName": workflow["route_name"],
        }
        for workflow in workflows
    ]
    return f"""import React, {{ useEffect, useMemo, useState }} from "react";
import {{ apiGet, apiPost }} from "../api/client";

const workflows = {json.dumps(workflow_data, indent=2)};

const buildInitialForms = () =>
  Object.fromEntries(
    workflows.map((workflow) => [
      workflow.storyKey,
      Object.fromEntries(workflow.fields.map((field) => [field, ""])),
    ]),
  );

export function {title}Page() {{
  const [forms, setForms] = useState(buildInitialForms);
  const [items, setItems] = useState([]);
  const [results, setResults] = useState({{}});
  const [activeWorkflow, setActiveWorkflow] = useState(workflows[0]?.storyKey || "");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const currentWorkflow = useMemo(
    () => workflows.find((workflow) => workflow.storyKey === activeWorkflow) || workflows[0],
    [activeWorkflow],
  );

  const load = async () => {{
    const data = await apiGet(workflows[0]?.listPath || "{_module_list_path(module)}");
    setItems(Array.isArray(data) ? data : []);
  }};

  useEffect(() => {{
    load();
  }}, []);

  const submit = async (event, workflow) => {{
    event.preventDefault();
    setLoading(true);
    setError("");
    try {{
      const data = await apiPost(workflow.submitPath, forms[workflow.storyKey] || {{}});
      setResults((previous) => ({{ ...previous, [workflow.storyKey]: data }}));
      setForms((previous) => ({{
        ...previous,
        [workflow.storyKey]: Object.fromEntries(workflow.fields.map((field) => [field, ""])),
      }}));
      await load();
    }} catch (requestError) {{
      setError(requestError.message);
    }} finally {{
      setLoading(false);
    }}
  }};

  return (
    <div className="module-shell">
      <section className="module-hero">
        <h2>{title}</h2>
        <p>Review the latest records, submit new entries, and manage this workflow from a single page.</p>
      </section>

      <div className="module-layout">
        <article className="module-panel">
          <div className="button-row">
            {{workflows.map((workflow) => (
              <button
                key={{workflow.storyKey}}
                type="button"
                className={{activeWorkflow === workflow.storyKey ? "primary-button" : "ghost-button"}}
                onClick={{() => setActiveWorkflow(workflow.storyKey)}}
              >
                {{workflow.storyKey.replace(/_/g, " ")}}
              </button>
            ))}}
          </div>

          {{currentWorkflow ? (
            <>
              <h3 style={{{{ marginTop: 20 }}}}>{{currentWorkflow.title}}</h3>
              <form onSubmit={{(event) => submit(event, currentWorkflow)}}>
                <div className="form-grid">
                  {{currentWorkflow.fields.map((field, index) => (
                    <label key={{field}} className={{index === currentWorkflow.fields.length - 1 && currentWorkflow.fields.length % 2 === 1 ? "field-span-full" : ""}}>
                      <span>{{field}}</span>
                      <input
                        value={{forms[currentWorkflow.storyKey]?.[field] || ""}}
                        onChange={{(event) =>
                          setForms((previous) => ({{
                            ...previous,
                            [currentWorkflow.storyKey]: {{
                              ...previous[currentWorkflow.storyKey],
                              [field]: event.target.value,
                            }},
                          }}))
                        }}
                      />
                    </label>
                  ))}}
                </div>
                <div className="button-row">
                  <button type="submit" className="primary-button" disabled={{loading}}>
                    {{loading ? "Saving..." : "Save"}}
                  </button>
                </div>
              </form>
            </>
          ) : null}}
          {{error ? <div className="feedback-banner error" style={{{{ marginTop: 16 }}}}>{{error}}</div> : null}}
          {{currentWorkflow && results[currentWorkflow.storyKey] ? (
            <div className="feedback-banner success" style={{{{ marginTop: 16 }}}}>
              {{results[currentWorkflow.storyKey].message || "Saved successfully"}}
            </div>
          ) : null}}
        </article>

        <aside className="module-panel">
          <div className="status-badge">{{items.length}} records loaded</div>
          <h4 style={{{{ marginTop: 16 }}}}>Persisted records</h4>
          <div className="record-stack">
            {{items.length ? items.map((item) => (
              <div key={{item.id}} className="record-card">
                <p><strong>Workflow:</strong> {{item.workflow}}</p>
                <p><strong>Status:</strong> {{item.status}}</p>
                <ul>
                  {{Object.entries(item.payload || {{}}).map(([key, value]) => (
                    <li key={{key}}><strong>{{key}}:</strong> {{String(value)}}</li>
                  ))}}
                </ul>
              </div>
            )) : <p className="muted">No records saved yet for this module.</p>}}
          </div>
        </aside>
      </div>
    </div>
  );
}}
"""


def _render_python_unit_test(module: str, workflow: dict[str, Any]) -> str:
    function_name = _python_create_function_name(workflow["story_key"])
    payload = {field: f"sample-{index}" for index, field in enumerate(workflow["fields"] or ["title"], start=1)}
    if module == "auth":
        auth_path = _workflow_submit_path(module, workflow)
        if auth_path == "/auth/register":
            payload = {"name": "Test User", "email": "tester@example.com", "password": "password123"}
        else:
            payload = {"email": "tester@example.com", "password": "password123"}
    field_names = list(payload.keys())
    if module == "auth":
        if "name" in payload:
            return f"""import uuid

import pytest
from fastapi import HTTPException

from database import get_connection
from services import {module}_service


def unique_email() -> str:
    return f"test-{{uuid.uuid4().hex[:12]}}@example.com"


def reset_auth_tables():
    {module}_service.ensure_tables()
    connection = get_connection()
    try:
        with connection:
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM auth_sessions")
                cursor.execute("DELETE FROM auth_audit_log")
                cursor.execute("DELETE FROM app_users")
                cursor.execute(
                    \"\"\"
                    INSERT INTO auth_sessions (id, user_id, session_token, is_authenticated)
                    VALUES (1, NULL, NULL, FALSE)
                    ON CONFLICT (id) DO NOTHING
                    \"\"\"
                )
    finally:
        connection.close()


def test_{workflow["story_key"]}_service_create_success():
    reset_auth_tables()
    payload = {payload!r}
    payload["email"] = unique_email()
    created = {module}_service.{function_name}(payload)
    assert created["message"] == "Account created successfully"
    assert created["user"]["email"] == payload["email"]


def test_{workflow["story_key"]}_service_duplicate_email_raises_http_error():
    reset_auth_tables()
    payload = {payload!r}
    payload["email"] = unique_email()
    {module}_service.{function_name}(payload)
    with pytest.raises(HTTPException) as exc_info:
        {module}_service.{function_name}(payload)
    assert exc_info.value.status_code == 409


def test_{workflow["story_key"]}_service_invalid_input_type_raises():
    reset_auth_tables()
    with pytest.raises(TypeError):
        {module}_service.{function_name}(None)


def test_{workflow["story_key"]}_service_missing_required_fields_raise_http_error():
    reset_auth_tables()
    with pytest.raises(HTTPException) as exc_info:
        {module}_service.{function_name}({{"email": unique_email()}})
    assert exc_info.value.status_code == 400


def test_{workflow["story_key"]}_service_database_error_is_visible():
    reset_auth_tables()
    payload = {payload!r}
    payload["email"] = unique_email()
    original_get_connection = {module}_service.get_connection
    call_count = {{"value": 0}}

    def flaky_connection():
        call_count["value"] += 1
        if call_count["value"] > 1:
            raise RuntimeError("db error")
        return original_get_connection()

    from unittest.mock import patch

    with patch("services.{module}_service.get_connection", side_effect=flaky_connection):
        with pytest.raises(RuntimeError, match="db error"):
            {module}_service.{function_name}(payload)
"""
        return f"""import uuid

import pytest
from fastapi import HTTPException

from database import get_connection
from services import {module}_service


def unique_email() -> str:
    return f"test-{{uuid.uuid4().hex[:12]}}@example.com"


def reset_auth_tables():
    {module}_service.ensure_tables()
    connection = get_connection()
    try:
        with connection:
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM auth_sessions")
                cursor.execute("DELETE FROM auth_audit_log")
                cursor.execute("DELETE FROM app_users")
                cursor.execute(
                    \"\"\"
                    INSERT INTO auth_sessions (id, user_id, session_token, is_authenticated)
                    VALUES (1, NULL, NULL, FALSE)
                    ON CONFLICT (id) DO NOTHING
                    \"\"\"
                )
    finally:
        connection.close()


def seed_user(password: str = "password123"):
    payload = {{"name": "Test User", "email": unique_email(), "password": password}}
    created = {module}_service.register_user(payload)
    return payload, created


def test_{workflow["story_key"]}_service_create_success():
    reset_auth_tables()
    seeded, _ = seed_user()
    created = {module}_service.{function_name}({{"email": seeded["email"], "password": seeded["password"]}})
    assert created["message"] == "Logged in successfully"
    assert created["user"]["email"] == seeded["email"]


def test_{workflow["story_key"]}_service_invalid_credentials_raise_http_error():
    reset_auth_tables()
    seeded, _ = seed_user()
    with pytest.raises(HTTPException) as exc_info:
        {module}_service.{function_name}({{"email": seeded["email"], "password": "wrong-password"}})
    assert exc_info.value.status_code == 401


def test_{workflow["story_key"]}_service_missing_required_fields_raise_http_error():
    reset_auth_tables()
    with pytest.raises(HTTPException) as exc_info:
        {module}_service.{function_name}({{"email": unique_email()}})
    assert exc_info.value.status_code == 400


def test_{workflow["story_key"]}_service_invalid_input_type_raises():
    reset_auth_tables()
    with pytest.raises(TypeError):
        {module}_service.{function_name}(None)


def test_{workflow["story_key"]}_service_database_error_is_visible():
    reset_auth_tables()
    seeded, _ = seed_user()
    original_get_connection = {module}_service.get_connection
    call_count = {{"value": 0}}

    def flaky_connection():
        call_count["value"] += 1
        if call_count["value"] > 1:
            raise RuntimeError("db error")
        return original_get_connection()

    from unittest.mock import patch

    with patch("services.{module}_service.get_connection", side_effect=flaky_connection):
        with pytest.raises(RuntimeError, match="db error"):
            {module}_service.{function_name}({{"email": seeded["email"], "password": seeded["password"]}})
"""
    return f"""from unittest.mock import patch

from database import get_connection
from services import {module}_service


def reset_table():
    {module}_service.ensure_table()
    connection = get_connection()
    connection.execute("DELETE FROM {module}_records")
    connection.commit()
    connection.close()


def test_{workflow["story_key"]}_service_create_success():
    reset_table()
    created = {module}_service.{function_name}({payload!r})
    assert created["workflow"] == "{workflow["route_name"]}"


def test_{workflow["story_key"]}_service_list_returns_collection():
    reset_table()
    assert isinstance({module}_service.list_items("{workflow["route_name"]}"), list)


def test_{workflow["story_key"]}_service_handles_multiple_records():
    reset_table()
    {module}_service.{function_name}({payload!r})
    {module}_service.{function_name}({payload!r})
    assert len({module}_service.list_items("{workflow["route_name"]}")) >= 2


def test_{workflow["story_key"]}_service_accepts_empty_strings():
    reset_table()
    result = {module}_service.{function_name}({{key: "" for key in {field_names!r}}})
    assert result["workflow"] == "{workflow["route_name"]}"


def test_{workflow["story_key"]}_service_accepts_boundary_payload():
    reset_table()
    boundary = "x" * 255
    result = {module}_service.{function_name}({{key: boundary for key in {field_names!r}}})
    assert all(value == boundary for value in result["data"].values())


def test_{workflow["story_key"]}_service_invalid_input_type_raises():
    reset_table()
    try:
        {module}_service.{function_name}(None)
    except Exception as exc:  # noqa: BLE001
        assert isinstance(exc, Exception)
    else:
        raise AssertionError("Expected invalid input to raise an error")


def test_{workflow["story_key"]}_service_database_error_is_visible():
    reset_table()
    with patch("services.{module}_service.get_connection", side_effect=RuntimeError("db error")):
        try:
            {module}_service.{function_name}({payload!r})
        except RuntimeError as exc:
            assert "db error" in str(exc)
        else:
            raise AssertionError("Expected database error")


def test_{workflow["story_key"]}_service_missing_field_path_still_returns_data():
    reset_table()
    result = {module}_service.{function_name}({{"unexpected": "value"}})
    assert "unexpected" in result["data"]
"""


def _render_python_integration_test(module: str, workflow: dict[str, Any]) -> str:
    path = _workflow_submit_path(module, workflow)
    body = {field: f"demo-{index}" for index, field in enumerate(workflow["fields"] or ["title"], start=1)}
    if module == "auth":
        if path == "/auth/register":
            return f"""import uuid

from fastapi.testclient import TestClient

from main import app


client = TestClient(app)


def unique_email() -> str:
    return f"test-{{uuid.uuid4().hex[:12]}}@example.com"


def test_{workflow["story_key"]}_endpoint_success():
    response = client.post("{path}", json={{"name": "Test User", "email": unique_email(), "password": "password123"}})
    assert response.status_code == 200


def test_{workflow["story_key"]}_endpoint_validation():
    response = client.post("{path}", json={{}})
    assert response.status_code in {{400, 422}}


def test_{workflow["story_key"]}_endpoint_incorrect_method():
    response = client.put("{path}", json={{"name": "Test User", "email": unique_email(), "password": "password123"}})
    assert response.status_code in {{405, 404}}


def test_{workflow["story_key"]}_endpoint_duplicate_email_returns_conflict():
    payload = {{"name": "Test User", "email": unique_email(), "password": "password123"}}
    first = client.post("{path}", json=payload)
    second = client.post("{path}", json=payload)
    assert first.status_code == 200
    assert second.status_code == 409


def test_{workflow["story_key"]}_endpoint_invalid_request():
    response = client.post("{path}", data="not-json")
    assert response.status_code in {{400, 422}}


def test_{workflow["story_key"]}_list_endpoint():
    response = client.get("/auth/sessions")
    assert response.status_code == 200
"""
        return f"""import uuid

from fastapi.testclient import TestClient

from main import app


client = TestClient(app)


def unique_email() -> str:
    return f"test-{{uuid.uuid4().hex[:12]}}@example.com"


def register_user():
    payload = {{"name": "Test User", "email": unique_email(), "password": "password123"}}
    response = client.post("/auth/register", json=payload)
    assert response.status_code == 200
    return payload


def test_{workflow["story_key"]}_endpoint_success():
    seeded = register_user()
    response = client.post("{path}", json={{"email": seeded["email"], "password": seeded["password"]}})
    assert response.status_code == 200


def test_{workflow["story_key"]}_endpoint_validation():
    response = client.post("{path}", json={{}})
    assert response.status_code in {{400, 422}}


def test_{workflow["story_key"]}_endpoint_incorrect_method():
    response = client.put("{path}", json={{"email": unique_email(), "password": "password123"}})
    assert response.status_code in {{405, 404}}


def test_{workflow["story_key"]}_endpoint_authentication_failure_shape():
    response = client.post("{path}", json={{"email": unique_email(), "password": "wrong-password"}})
    assert response.status_code == 401


def test_{workflow["story_key"]}_endpoint_invalid_request():
    response = client.post("{path}", data="not-json")
    assert response.status_code in {{400, 422}}


def test_{workflow["story_key"]}_list_endpoint():
    response = client.get("/auth/sessions")
    assert response.status_code == 200
"""
    get_path = _module_list_path(module)
    invalid_body = {"email": "bad@example.com"} if module == "auth" else {}
    return f"""from fastapi.testclient import TestClient

from main import app


client = TestClient(app)


def test_{workflow["story_key"]}_endpoint_success():
    response = client.post("{path}", json={body!r})
    assert response.status_code == 200


def test_{workflow["story_key"]}_endpoint_validation():
    response = client.post("{path}", json={{}})
    assert response.status_code in {{200, 422}}


def test_{workflow["story_key"]}_endpoint_incorrect_method():
    response = client.put("{path}", json={body!r})
    assert response.status_code in {{405, 404}}


def test_{workflow["story_key"]}_endpoint_authentication_failure_shape():
    response = client.post("{path}", json={invalid_body!r})
    assert response.status_code in {{200, 422}}


def test_{workflow["story_key"]}_endpoint_invalid_request():
    response = client.post("{path}", data="not-json")
    assert response.status_code in {{200, 422}}


def test_{workflow["story_key"]}_list_endpoint():
    response = client.get("{get_path}")
    assert response.status_code == 200
"""


def _render_node_backend_package_json() -> str:
    return json.dumps(
        {
            "name": "generated-story-backend",
            "private": True,
            "version": "0.0.1",
            "scripts": {"dev": "node server.js"},
            "dependencies": {
                "cors": "^2.8.5",
                "express": "^4.21.0",
                "sqlite3": "^5.1.7",
            },
        },
        indent=2,
    )


def _render_node_server(story_registry: dict[str, list[dict[str, Any]]]) -> str:
    handlers = []
    for module, workflows in story_registry.items():
        handlers.append(f'app.get("{_module_list_path(module)}", (_req, res) => res.json(state.{module}));')
        for workflow in workflows:
            handlers.append(
                f"""
app.post("{_workflow_submit_path(module, workflow)}", (req, res) => {{
  const item = {{ id: state.{module}.length + 1, workflow: "{workflow["route_name"]}", ...req.body }};
  state.{module}.push(item);
  res.json({{ message: "{workflow.get("display_title") or workflow["story_title"]} completed", data: item }});
}});
""".strip()
            )
    return f"""const express = require("express");
const cors = require("cors");

const app = express();
const state = {{
  {", ".join(f"{module}: []" for module in story_registry)}
}};

app.use(cors({{ origin: ["http://localhost:5173", "http://localhost:5174"] }}));
app.use(express.json());

{chr(10).join(handlers)}

app.get("/health", (_req, res) => res.json({{ status: "ok" }}));

app.listen(8001, () => {{
  console.log("Generated backend running on http://localhost:8001");
}});
"""


def _render_node_test(module: str, workflow: dict[str, Any]) -> str:
    route = _workflow_submit_path(module, workflow)
    body = {field: f"demo-{index}" for index, field in enumerate(workflow["fields"] or ["title"], start=1)}
    if module == "auth":
        body = {"email": "tester@example.com", "password": "password123"}
    return f"""test("{workflow["story_key"]} endpoint returns success", async () => {{
  const response = await fetch("http://localhost:8001{route}", {{
    method: "POST",
    headers: {{ "Content-Type": "application/json" }},
    body: JSON.stringify({body!r})
  }});
  expect(response.status).toBe(200);
}});

test("{workflow["story_key"]} endpoint invalid payload", async () => {{
  const response = await fetch("http://localhost:8001{route}", {{
    method: "POST",
    headers: {{ "Content-Type": "application/json" }},
    body: JSON.stringify({{}})
  }});
  expect([200, 400, 422]).toContain(response.status);
}});
"""


def _manual_test_cases(story: dict[str, Any], module: str) -> list[dict[str, Any]]:
    title = str(story.get("title") or story.get("summary") or _title_case(module))
    scenario_templates = [
        ("success", "Enter valid values and submit the form."),
        ("invalid-input", "Enter invalid values and verify inline validation."),
        ("missing-fields", "Submit the form with required fields missing."),
        ("boundary", "Use boundary-length values and submit."),
        ("regression", "Verify previously generated module pages still work after this story."),
    ]
    cases = []
    for index, (category, focus) in enumerate(scenario_templates, start=1):
        cases.append(
            {
                "id": f"M-{module.upper()}-{index:03d}",
                "title": f"{title} - {category.replace('-', ' ').title()}",
                "category": category,
                "preconditions": ["Generated application is running locally."],
                "steps": [
                    f"Open the {_title_case(module)} page on http://localhost:5174.",
                    focus,
                    "Observe the API response and resulting record list.",
                ],
                "expected_result": "The UI updates correctly and previously generated flows remain usable.",
                "priority": "High",
            }
        )
    return cases


def _automated_test_case(story: dict[str, Any], module: str) -> dict[str, Any]:
    return {
        "id": f"A-{module.upper()}-001",
        "title": str(story.get("title") or story.get("summary") or _title_case(module)),
        "category": "integration",
        "type": "api",
        "test_data": _extract_fields(story),
        "assertions": ["Endpoint responds with 200", "Generated module returns structured JSON"],
        "priority": "High",
    }


def _render_manual_tests_markdown(stories: list[dict[str, Any]]) -> str:
    blocks = ["# Manual Test Cases", ""]
    for story in stories:
        module = _extract_module_name(story)
        blocks.extend(
            [
                f"## {story.get('title') or story.get('summary') or _title_case(module)}",
                "",
                "Steps:",
                "1. Open the generated application on `http://localhost:5174`.",
                "2. Sign in if authentication is enabled, then navigate to the relevant module page.",
                "3. Enter valid values in the generated form fields.",
                "4. Submit the form and verify the API response panel updates.",
                "",
                "Expected Result:",
                "The module accepts input, persists or lists data, and does not break earlier story flows.",
                "",
            ]
        )
    return "\n".join(blocks).strip()


def _render_runtime_engine_source(selected_language: str) -> str:
    backend_start = (
        '[sys.executable, "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]'
        if selected_language == "python"
        else '["node", "server.js"]'
    )
    return f"""from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


class RuntimeEngine:
    def __init__(self, root_dir: str = "generated_project") -> None:
        self.root_dir = Path(root_dir).resolve()
        self.root_dir.mkdir(parents=True, exist_ok=True)
        self.backend_process = None
        self.frontend_process = None

    def _safe_path(self, relative_path: str) -> Path:
        target = (self.root_dir / relative_path).resolve()
        if self.root_dir not in target.parents and target != self.root_dir:
            raise ValueError("Unsafe path")
        return target

    def write_files(self, files: dict[str, str]) -> None:
        for relative_path, content in files.items():
            target = self._safe_path(relative_path)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")

    def install_dependencies(self) -> None:
        backend_requirements = self.root_dir / "backend" / "requirements.txt"
        if backend_requirements.exists():
            subprocess.run([sys.executable, "-m", "pip", "install", "-r", str(backend_requirements)], check=False)
        if (self.root_dir / "frontend" / "package.json").exists():
            subprocess.run(["npm", "install"], cwd=self.root_dir / "frontend", check=False)

    def start(self) -> dict[str, str]:
        env = os.environ.copy()
        self.backend_process = subprocess.Popen({backend_start}, cwd=self.root_dir / "backend", env=env)
        self.frontend_process = subprocess.Popen(
            ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5174"],
            cwd=self.root_dir / "frontend",
            env=env,
        )
        return {{"backend_url": "http://localhost:8001", "preview_url": "http://localhost:5174"}}
"""


def _render_preview_api_source() -> str:
    return """from fastapi import FastAPI
from pydantic import BaseModel

from runtime_engine import RuntimeEngine


class PreviewRequest(BaseModel):
    files: dict[str, str]


app = FastAPI()
engine = RuntimeEngine()


@app.post("/preview-project")
def preview_project(payload: PreviewRequest):
    engine.write_files(payload.files)
    engine.install_dependencies()
    return engine.start()
"""


def _ensure_python_package_files(rendered_files: dict[str, str], include_test_files: bool = True) -> None:
    rendered_files.setdefault("backend/__init__.py", "")
    rendered_files.setdefault("backend/routers/__init__.py", "")
    rendered_files.setdefault("backend/services/__init__.py", "")
    if include_test_files:
        rendered_files.setdefault("tests/__init__.py", "")
        rendered_files.setdefault("tests/unit/__init__.py", "")
        rendered_files.setdefault("tests/integration/__init__.py", "")


def _build_story_increment(
    story: dict[str, Any],
    selected_language: str,
    existing_project_files: dict[str, str],
    *,
    project_config: dict[str, Any] | None = None,
    include_test_files: bool = True,
) -> dict[str, Any]:
    resolved_project_config = normalize_project_config(selected_language, project_config)
    story_registry = _read_story_registry(existing_project_files)
    existing_modules = _read_modules_registry(existing_project_files) or sorted(story_registry)
    specification = build_language_neutral_spec(story)
    workflow = _build_story_workflow(story, specification, story_registry.get(specification["module"], []))
    story_registry = _upsert_story_registry(story_registry, workflow)

    registry_specs = [
        {
            "module": module_name,
            "functions": [
                {
                    "name": f"{module_name}_workflow",
                    "inputs": item.get("fields", []),
                    "outputs": item.get("outputs", ["result"]),
                    "logic_steps": item.get("logic_steps", []),
                    "dependencies": ["data_store"],
                }
                for item in workflows
            ],
        }
        for module_name, workflows in story_registry.items()
    ]

    architecture = build_application_architecture(registry_specs or [specification], selected_language, existing_modules)
    all_modules = architecture["modules"]
    module = workflow["module"]
    module_workflows = story_registry[module]
    title = _title_case(module)

    rendered_files: dict[str, str] = {
        "modules.json": json.dumps({"modules": all_modules}, indent=2),
        "story_registry.json": json.dumps({"modules": story_registry}, indent=2),
        "docs/manual_tests.md": _render_manual_tests_markdown(_registry_stories(story_registry)),
        "runtime_engine.py": _render_runtime_engine_source(selected_language),
        "preview_api.py": _render_preview_api_source(),
    }
    tests: dict[str, str] = {}

    if selected_language == "python":
        backend_requirements = [
            "fastapi>=0.115.0",
            "uvicorn>=0.30.6",
            "pydantic>=2.9.2",
            "jinja2>=3.1.4",
            "psycopg2-binary>=2.9.9",
            "python-dotenv>=1.0.1",
        ]
        if module == "auth":
            backend_requirements.append("email-validator>=2.2.0")
        if include_test_files:
            backend_requirements.extend(["httpx>=0.27.2", "pytest>=8.3.3"])

        rendered_files.update(
            {
                "backend/main.py": _render_python_backend_main(all_modules),
                "backend/database.py": _render_python_database(),
                "backend/.env.example": (
                    "DATABASE_URL=postgresql://postgres:postgres@localhost:5432/generated_story_app\n"
                    if resolved_project_config["database"] == "postgresql"
                    else ""
                ),
                "backend/requirements.txt": "\n".join(backend_requirements) + "\n",
                "frontend/package.json": _render_frontend_package_json(),
                "frontend/vite.config.js": _render_frontend_vite_config(),
                "frontend/index.html": '<!doctype html><html><body><div id="root"></div><script type="module" src="/src/main.jsx"></script></body></html>',
                "frontend/src/main.jsx": _render_frontend_main(),
                "frontend/src/App.jsx": _render_frontend_app(all_modules),
                "frontend/src/styles.css": _render_frontend_styles(),
                "frontend/src/config/api.js": _render_frontend_api_config(),
                "frontend/src/api/client.js": _render_frontend_api_client(),
                f"backend/services/{module}_service.py": (
                    _render_python_auth_service() if module == "auth" else _render_python_service(module, module_workflows)
                ),
                f"backend/routers/{module}_router.py": (
                    _render_python_auth_router() if module == "auth" else _render_python_router(module, module_workflows)
                ),
                f"frontend/src/pages/{title}Page.jsx": _render_frontend_page(module, module_workflows),
            }
        )
        if include_test_files:
            tests[f"tests/unit/test_{module}_{workflow['story_key']}_service.py"] = _render_python_unit_test(module, workflow)
            tests[f"tests/integration/test_{module}_{workflow['story_key']}_api.py"] = _render_python_integration_test(module, workflow)
        _ensure_python_package_files(rendered_files, include_test_files=include_test_files)
    else:
        rendered_files.update(
            {
                "backend/package.json": _render_node_backend_package_json(),
                "backend/server.js": _render_node_server(story_registry),
                "frontend/package.json": _render_frontend_package_json(),
                "frontend/vite.config.js": _render_frontend_vite_config(),
                "frontend/index.html": '<!doctype html><html><body><div id="root"></div><script type="module" src="/src/main.jsx"></script></body></html>',
                "frontend/src/main.jsx": _render_frontend_main(),
                "frontend/src/App.jsx": _render_frontend_app(all_modules),
                "frontend/src/styles.css": _render_frontend_styles(),
                "frontend/src/config/api.js": _render_frontend_api_config(),
                "frontend/src/api/client.js": _render_frontend_api_client(),
                f"frontend/src/pages/{title}Page.jsx": _render_frontend_page(module, module_workflows),
            }
        )
        if include_test_files:
            tests[f"tests/unit/{module}.{workflow['story_key']}.test.js"] = _render_node_test(module, workflow)
            tests[f"tests/integration/{module}.{workflow['story_key']}.integration.test.js"] = _render_node_test(module, workflow)

    if include_test_files:
        rendered_files.update(tests)

    new_files: dict[str, str] = {}
    modified_files: dict[str, str] = {}
    for path, content in rendered_files.items():
        if path in existing_project_files:
            if existing_project_files[path] != content:
                modified_files[path] = content
        else:
            new_files[path] = content

    return {
        "architecture": json.dumps(architecture, indent=2),
        "specification": specification,
        "generated_files": rendered_files,
        "new_files": new_files,
        "modified_files": modified_files,
        "tests": tests,
        "manual_tests": rendered_files["docs/manual_tests.md"],
        "manual_test_cases": _manual_test_cases(story, module),
        "automated_test_cases": [_automated_test_case(story, module)],
        "runtime_engine": rendered_files["runtime_engine.py"],
        "preview_api": rendered_files["preview_api.py"],
    }


def run_generated_tests(files: dict[str, str], selected_language: str) -> dict[str, Any]:
    if selected_language != "python":
        return {"success_rate": 1.0, "ok": True, "message": "Validation skipped for non-Python stack."}

    test_paths = sorted(path for path in files if path.startswith("tests/") and path.endswith(".py"))
    result = run_project_unit_tests(files, "python_fastapi", test_paths)
    success_rate = 1.0 if result.get("ok") else 0.0
    return {
        "success_rate": success_rate,
        "ok": bool(result.get("ok")),
        "message": result.get("message", ""),
        "stdout": result.get("stdout", ""),
        "stderr": result.get("stderr", ""),
    }


def _refresh_live_preview(project_id: str, files: dict[str, str]) -> str:
    project_path = _RUNTIME_MANAGER.create_workspace(project_id)
    _RUNTIME_MANAGER.write_files(project_path, files)
    marker = project_path / ".dependencies_installed"
    if not marker.exists():
        _RUNTIME_MANAGER.install_dependencies(project_path)
        marker.write_text("installed", encoding="utf-8")
    _RUNTIME_MANAGER.restart_backend(project_path)
    _RUNTIME_MANAGER.restart_frontend(project_path)
    return _RUNTIME_MANAGER.get_preview_url()


def run_post_story_pipeline(
    stories: list[dict[str, Any]],
    selected_language: str,
    existing_project_files: dict[str, str] | None = None,
    *,
    project_config: dict[str, Any] | None = None,
    project_id: str = "generated-story-preview",
    enable_live_preview: bool = False,
    include_test_files: bool = True,
) -> dict[str, Any]:
    merged_files = dict(existing_project_files or {})
    story_results: list[dict[str, Any]] = []
    specifications: list[dict[str, Any]] = []
    all_tests: dict[str, str] = {}
    all_manual_cases: list[dict[str, Any]] = []
    all_automated_cases: list[dict[str, Any]] = []
    latest_output: dict[str, Any] = {}

    for story in stories:
        final_validation: dict[str, Any] = {
            "success_rate": 1.0 if not include_test_files else 0.0,
            "ok": not include_test_files,
            "message": "Validation skipped because test file generation is disabled." if not include_test_files else "Not run",
        }
        story_output: dict[str, Any] = {}
        if include_test_files:
            for attempt in range(1, 4):
                story_output = _build_story_increment(
                    story,
                    selected_language,
                    merged_files,
                    project_config=project_config,
                    include_test_files=include_test_files,
                )
                candidate_files = dict(merged_files)
                candidate_files.update(story_output["generated_files"])
                final_validation = run_generated_tests(candidate_files, selected_language)
                if final_validation["success_rate"] >= 0.95:
                    merged_files = candidate_files
                    break
                if attempt == 3:
                    merged_files = candidate_files
        else:
            story_output = _build_story_increment(
                story,
                selected_language,
                merged_files,
                project_config=project_config,
                include_test_files=include_test_files,
            )
            candidate_files = dict(merged_files)
            candidate_files.update(story_output["generated_files"])
            merged_files = candidate_files

        preview_url = ""
        if enable_live_preview:
            preview_url = _refresh_live_preview(project_id, merged_files)

        latest_output = story_output
        specifications.append(story_output["specification"])
        all_tests.update(story_output["tests"])
        all_manual_cases.extend(story_output["manual_test_cases"])
        all_automated_cases.extend(story_output["automated_test_cases"])
        story_results.append(
            {
                "story_title": str(story.get("title") or story.get("summary") or "Story"),
                "status": "completed" if final_validation["success_rate"] >= 0.95 else "completed_with_warnings",
                "preview_url": preview_url or "http://localhost:5174",
                "test_success_rate": final_validation["success_rate"],
            }
        )

    new_files: dict[str, str] = {}
    modified_files: dict[str, str] = {}
    existing_snapshot = existing_project_files or {}
    for path, content in merged_files.items():
        if path in existing_snapshot:
            if existing_snapshot[path] != content:
                modified_files[path] = content
        else:
            new_files[path] = content

    return {
        "architecture": latest_output.get("architecture", "{}"),
        "generated_files": merged_files,
        "new_files": new_files,
        "modified_files": modified_files,
        "tests": all_tests,
        "manual_tests": _render_manual_tests_markdown(stories),
        "manual_test_cases": all_manual_cases,
        "automated_test_cases": all_automated_cases,
        "runtime_engine": latest_output.get("runtime_engine", _render_runtime_engine_source(selected_language)),
        "preview_api": latest_output.get("preview_api", _render_preview_api_source()),
        "specifications": specifications,
        "story_results": story_results,
        "preview_url": story_results[-1]["preview_url"] if story_results else "",
        "test_generation_strategy": {
            "unit_tests_per_story": 8 if include_test_files else 0,
            "integration_tests_per_story": 5 if include_test_files else 0,
            "manual_tests_per_story": 5,
            "retry_limit": 3,
            "target_success_rate": 0.95 if include_test_files else 1.0,
        },
    }

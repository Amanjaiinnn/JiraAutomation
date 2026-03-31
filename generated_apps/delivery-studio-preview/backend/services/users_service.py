import json

from database import get_connection


TABLE_NAME = "users_records"


def ensure_table():
    connection = get_connection()
    with connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS users_records (
                    id SERIAL PRIMARY KEY,
                    workflow TEXT NOT NULL,
                    payload JSONB NOT NULL,
                    status TEXT NOT NULL
                )
                """
            )
    connection.close()


def list_items(workflow: str | None = None):
    ensure_table()
    connection = get_connection()
    with connection.cursor() as cursor:
        if workflow:
            cursor.execute(
                "SELECT id, workflow, payload, status FROM users_records WHERE workflow = %s ORDER BY id DESC",
                (workflow,),
            )
        else:
            cursor.execute(
                "SELECT id, workflow, payload, status FROM users_records ORDER BY id DESC"
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
                "INSERT INTO users_records (workflow, payload, status) VALUES (%s, %s::jsonb, %s)",
                (workflow, json.dumps(data), "created"),
            )
    connection.close()
    return {
        "message": success_message,
        "workflow": workflow,
        "fields": expected_fields,
        "data": data,
    }


def create_user_create(data: dict):
    return _create_record(
        workflow="create-task-title",
        data=data,
        expected_fields=['title', 'details'],
        success_message="As a user, I want to create a task with title, description, due date, and priority so that I can manage my tasks efficiently. completed",
    )

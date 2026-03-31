from fastapi import APIRouter
from pydantic import BaseModel

from services import tasks_service


class UserCreateRequest(BaseModel):
    title: str
    description: str
    due_date: str
    priority: str


router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("")
def list_tasks():
    return tasks_service.list_items()
@router.post("/create-task-title")
def submit_user_create(payload: UserCreateRequest):
    response = tasks_service.create_user_create(payload.model_dump())
    
    return response
@router.post("")
def create_tasks(payload: UserCreateRequest):
    return tasks_service.create_user_create(payload.model_dump())

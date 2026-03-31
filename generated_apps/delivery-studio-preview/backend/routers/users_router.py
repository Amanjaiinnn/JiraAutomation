from fastapi import APIRouter
from pydantic import BaseModel

from services import users_service


class UserCreateRequest(BaseModel):
    title: str
    details: str


router = APIRouter(prefix="/users", tags=["users"])


@router.get("")
def list_users():
    return users_service.list_items()
@router.post("/create-task-title")
def submit_user_create(payload: UserCreateRequest):
    response = users_service.create_user_create(payload.model_dump())
    
    return response
@router.post("")
def create_users(payload: UserCreateRequest):
    return users_service.create_user_create(payload.model_dump())

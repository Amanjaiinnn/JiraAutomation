from fastapi import APIRouter
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

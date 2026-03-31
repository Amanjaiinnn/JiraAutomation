from fastapi import APIRouter
from pydantic import BaseModel

from services import story_service


class StoryRequest(BaseModel):
    title: str
    details: str


router = APIRouter(prefix="/story", tags=["story"])


@router.get("")
def list_story():
    return story_service.list_items()
@router.post("/submit")
def submit_story(payload: StoryRequest):
    response = story_service.create_story(payload.model_dump())
    
    return response
@router.post("")
def create_story(payload: StoryRequest):
    return story_service.create_story(payload.model_dump())

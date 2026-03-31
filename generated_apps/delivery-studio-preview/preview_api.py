from fastapi import FastAPI
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

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import auth_router
from routers import tasks_router

app = FastAPI(title="Generated Story App")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router)
app.include_router(tasks_router.router)


@app.get("/health")
def health():
    return {"status": "ok"}

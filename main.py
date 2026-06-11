from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse

from auth import get_optional_user, require_admin
from config import API_KEYS
from db_postgres import init_db
from services.gemini import ingest_project_docs
from routers import activity_router, auth_router, emails_router, patients_router, prescriptions_router, rag_router

BASE_DIR = Path(__file__).resolve().parent


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    # Initialize RAG vector store on startup
    try:
        ingest_project_docs(max_docs=500)
    except Exception as e:
        print(f"⚠️  RAG ingestion skipped: {e}")
    yield


app = FastAPI(title="MedRemind", lifespan=lifespan)

app.include_router(auth_router.router)
app.include_router(patients_router.router)
app.include_router(prescriptions_router.router)
app.include_router(emails_router.router)
app.include_router(activity_router.router)
app.include_router(rag_router.router)


@app.get("/")
def root():
    return {"message": "MedRemind API is running", "docs": "/docs"}


@app.get("/admin/{page}")
def admin_page(page: str, user: dict = Depends(require_admin)):
    return {"page": page, "user": user}


@app.get("/admin")
def admin_root():
    return RedirectResponse("/docs", status_code=302)
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from auth import get_optional_user, require_admin
from config import API_KEYS
from db_postgres import init_db
from routers import activity_router, auth_router, emails_router, patients_router, prescriptions_router

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="MedRemind", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

app.include_router(auth_router.router)
app.include_router(patients_router.router)
app.include_router(prescriptions_router.router)
app.include_router(emails_router.router)
app.include_router(activity_router.router)

NAV_PAGES = [
    ("dashboard", "Dashboard"),
    ("prescription", "Prescription Upload"),
    ("patients", "Patient Records"),
    ("email", "Email Reminder"),
    ("activity", "Activity"),
]


def user_initials(user: dict) -> str:
    name = (user or {}).get("full_name", "").strip()
    if name:
        parts = name.split()
        if len(parts) >= 2:
            return (parts[0][0] + parts[-1][0]).upper()
        return name[0].upper()
    email = (user or {}).get("email", "")
    return email[0].upper() if email else "?"


def admin_context(request: Request, user: dict, page: str, **extra):
    return {
        "request": request,
        "user": user,
        "initials": user_initials(user),
        "nav_pages": NAV_PAGES,
        "active_page": page,
        "gemini_configured": bool(API_KEYS),
        **extra,
    }


@app.get("/", response_class=HTMLResponse)
def login_page(request: Request, user: dict | None = Depends(get_optional_user)):
    if user and user.get("role") == "admin":
        return RedirectResponse("/admin/dashboard", status_code=302)
    return templates.TemplateResponse("login.html", {"request": request})


@app.get("/admin/{page}", response_class=HTMLResponse)
def admin_page(page: str, request: Request, user: dict = Depends(require_admin)):
    valid = {p[0] for p in NAV_PAGES}
    if page not in valid:
        raise HTTPException(status_code=404, detail="Page not found")
    template = f"admin/{page}.html"
    return templates.TemplateResponse(
        template,
        admin_context(request, user, page),
    )


@app.get("/admin")
def admin_root():
    return RedirectResponse("/admin/dashboard", status_code=302)

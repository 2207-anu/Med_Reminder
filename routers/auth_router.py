from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, EmailStr, Field

from auth import (
    COOKIE_NAME,
    authenticate,
    create_access_token,
    get_current_user,
    require_admin,
    signup,
    valid_email,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class SignupRequest(BaseModel):
    full_name: str = Field(min_length=1)
    email: EmailStr
    password: str = Field(min_length=8)
    confirm_password: str


def _set_auth_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        max_age=86400,
        samesite="lax",
    )


@router.post("/login")
def api_login(body: LoginRequest, response: Response):
    if not valid_email(body.email):
        raise HTTPException(status_code=400, detail="Enter a valid email")
    result = authenticate(body.email, body.password)
    if not result["success"]:
        raise HTTPException(status_code=401, detail=result["message"])
    if result["user"]["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access only. Sign up as a doctor.")
    token = create_access_token(result["user"])
    _set_auth_cookie(response, token)
    return {"success": True, "user": result["user"]}


@router.post("/signup")
def api_signup(body: SignupRequest, response: Response):
    if body.password != body.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords don't match")
    result = signup(body.full_name, body.email, body.password, role="admin")
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return {"success": True, "message": "Account created! Please login."}


@router.post("/logout")
def api_logout(response: Response):
    response.delete_cookie(COOKIE_NAME)
    return {"success": True}


@router.get("/me")
def api_me(user: dict = Depends(get_current_user)):
    return {"user": user}

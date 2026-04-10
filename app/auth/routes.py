from fastapi import APIRouter, HTTPException, Depends, Form
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from app.database import get_db
from app.auth.utils import hash_password, verify_password, create_access_token, decode_token
import uuid

router = APIRouter(prefix="/api/auth", tags=["auth"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")

# --- Schemas ---
class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

# --- Get current user ---
def get_current_user(token: str = Depends(oauth2_scheme)):
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return payload

# --- Routes ---
@router.post("/register")
def register(req: RegisterRequest):
    db = get_db()

    existing = db.table("tenants").select("id").eq("email", req.email).execute()
    if existing.data:
        raise HTTPException(status_code=400, detail="Email already registered")

    tenant_id = str(uuid.uuid4())
    hashed = hash_password(req.password)

    db.table("tenants").insert({
        "id": tenant_id,
        "name": req.name,
        "email": req.email,
        "plan": "starter",
        "billing_status": "trial",
        "region": "india",
        "camera_quota": 1,
        "storage_quota_gb": 50,
        "retention_days": 7,
        "password_hash": hashed
    }).execute()

    token = create_access_token({
        "sub": tenant_id,
        "email": req.email,
        "plan": "starter"
    })

    return {"access_token": token, "token_type": "bearer", "tenant_id": tenant_id}

# --- Swagger UI login (OAuth2 form) ---
@router.post("/token")
def token(form_data: OAuth2PasswordRequestForm = Depends()):
    db = get_db()

    result = db.table("tenants").select("*").eq("email", form_data.username).execute()
    if not result.data:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    tenant = result.data[0]

    if not verify_password(form_data.password, tenant.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token({
        "sub": tenant["id"],
        "email": tenant["email"],
        "plan": tenant["plan"]
    })

    return {"access_token": token, "token_type": "bearer"}

# --- JSON login (for frontend/app) ---
@router.post("/login")
def login(req: LoginRequest):
    db = get_db()

    result = db.table("tenants").select("*").eq("email", req.email).execute()
    if not result.data:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    tenant = result.data[0]

    if not verify_password(req.password, tenant.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token({
        "sub": tenant["id"],
        "email": tenant["email"],
        "plan": tenant["plan"]
    })

    return {"access_token": token, "token_type": "bearer", "tenant_id": tenant["id"]}

@router.get("/me")
def me(current_user: dict = Depends(get_current_user)):
    return current_user

@router.post("/logout")
def logout():
    return {"message": "Logged out successfully"}

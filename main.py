import os
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import (
    FastAPI,
    Depends,
    UploadFile,
    File as FastAPIFile
)

from fastapi.responses import Response, HTMLResponse
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles

from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import SessionLocal
from models import User, File, AuditLog
from auth import hash_password, verify_password
from encryption import encrypt_file, decrypt_file
from security import (
    create_access_token,
    verify_token,
    security
)
from services.code_service import generate_file_code


app = FastAPI()


# -------------------------
# STATIC FRONTEND FILES
# -------------------------

app.mount(
    "/static",
    StaticFiles(directory="frontend"),
    name="static"
)


# -------------------------
# FRONTEND PAGES
# -------------------------

@app.get("/", response_class=HTMLResponse)
def login_page():
    with open(
        "frontend/login.html",
        "r",
        encoding="utf-8"
    ) as file:
        return file.read()


@app.get("/register", response_class=HTMLResponse)
def register_page():
    with open(
        "frontend/register.html",
        "r",
        encoding="utf-8"
    ) as file:
        return file.read()


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard_page():
    with open(
        "frontend/dashboard.html",
        "r",
        encoding="utf-8"
    ) as file:
        return file.read()


# -------------------------
# DATABASE SESSION
# -------------------------

def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


# -------------------------
# AUDIT LOG HELPER
# -------------------------

def create_audit_log(
    db: Session,
    action: str,
    user_id: int = None,
    file_id: int = None,
    details: str = None
):
    log = AuditLog(
        user_id=user_id,
        action=action,
        file_id=file_id,
        details=details
    )

    db.add(log)
    db.commit()


# -------------------------
# ABOUT
# -------------------------

@app.get("/about")
def about():
    return {
        "project": "Secure File Sharing System"
    }


# -------------------------
# USER REGISTRATION
# -------------------------

class RegisterUser(BaseModel):
    username: str
    email: str
    password: str


@app.post("/register")
def register(
    user: RegisterUser,
    db: Session = Depends(get_db)
):
    existing_user = db.query(User).filter(
        User.username == user.username
    ).first()

    if existing_user:
        return {
            "message": "Username already exists"
        }

    hashed_password = hash_password(
        user.password
    )

    new_user = User(
        username=user.username,
        email=user.email,
        password_hash=hashed_password
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    create_audit_log(
        db=db,
        action="REGISTER",
        user_id=new_user.id,
        details=f"User '{new_user.username}' registered"
    )

    return {
        "message": "User registered successfully",
        "username": new_user.username
    }


# -------------------------
# USER LOGIN
# -------------------------

class LoginUser(BaseModel):
    username: str
    password: str


@app.post("/login")
def login(
    user: LoginUser,
    db: Session = Depends(get_db)
):
    existing_user = db.query(User).filter(
        User.username == user.username
    ).first()

    if not existing_user:
        return {
            "message": "Invalid username or password"
        }

    password_correct = verify_password(
        user.password,
        existing_user.password_hash
    )

    if not password_correct:
        return {
            "message": "Invalid username or password"
        }

    access_token = create_access_token(
        existing_user.id,
        existing_user.username
    )

    create_audit_log(
        db=db,
        action="LOGIN",
        user_id=existing_user.id,
        details=f"User '{existing_user.username}' logged in"
    )

    return {
        "message": "Login successful",
        "username": existing_user.username,
        "access_token": access_token,
        "token_type": "bearer"
    }


# -------------------------
# FILE UPLOAD
# -------------------------

@app.post("/upload")
async def upload_file(
    uploaded_file: UploadFile = FastAPIFile(...),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    current_user = verify_token(credentials)

    user_id = current_user["user_id"]

    user = db.query(User).filter(
        User.id == user_id
    ).first()

    if not user:
        return {
            "message": "User not found"
        }

    file_data = await uploaded_file.read()

    encrypted_data = encrypt_file(
        file_data
    )

    file_code = generate_file_code()

    expires_at = (
        datetime.now(timezone.utc)
        + timedelta(hours=1)
    )

    stored_filename = (
        f"{uuid.uuid4().hex}.enc"
    )

    os.makedirs(
        "storage",
        exist_ok=True
    )

    storage_path = os.path.join(
        "storage",
        stored_filename
    )

    with open(
        storage_path,
        "wb"
    ) as f:
        f.write(encrypted_data)

    new_file = File(
        filename=uploaded_file.filename,
        stored_filename=stored_filename,
        owner_id=user.id,
        file_code=file_code,
        expires_at=expires_at
    )

    db.add(new_file)
    db.commit()
    db.refresh(new_file)

    create_audit_log(
        db=db,
        action="FILE_UPLOAD",
        user_id=user.id,
        file_id=new_file.id,
        details=f"File '{uploaded_file.filename}' uploaded and encrypted"
    )

    return {
        "message": "File uploaded and encrypted successfully",
        "filename": uploaded_file.filename,
        "file_id": new_file.id,
        "owner": user.username,
        "code": file_code,
        "expires_at": expires_at
    }


# -------------------------
# FILE DOWNLOAD BY OWNER
# -------------------------

@app.get("/download/{file_id}")
def download_file(
    file_id: int,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    current_user = verify_token(credentials)

    user_id = current_user["user_id"]

    file_record = db.query(File).filter(
        File.id == file_id
    ).first()

    if not file_record:
        return {
            "message": "File not found"
        }

    if file_record.owner_id != user_id:

        create_audit_log(
            db=db,
            action="ACCESS_DENIED",
            user_id=user_id,
            file_id=file_record.id,
            details=f"Unauthorized access attempt on '{file_record.filename}'"
        )

        return {
            "message": "Access denied"
        }

    storage_path = os.path.join(
        "storage",
        file_record.stored_filename
    )

    if not os.path.exists(storage_path):
        return {
            "message": "Encrypted file not found"
        }

    with open(
        storage_path,
        "rb"
    ) as f:
        encrypted_data = f.read()

    decrypted_data = decrypt_file(
        encrypted_data
    )

    create_audit_log(
        db=db,
        action="FILE_DOWNLOAD",
        user_id=user_id,
        file_id=file_record.id,
        details=f"Owner downloaded '{file_record.filename}'"
    )

    return Response(
        content=decrypted_data,
        media_type="application/octet-stream",
        headers={
            "Content-Disposition":
                f'attachment; filename="{file_record.filename}"'
        }
    )


# -------------------------
# FILE DOWNLOAD BY CODE
# -------------------------

class FileCodeRequest(BaseModel):
    code: str


@app.post("/download-by-code")
def download_by_code(
    data: FileCodeRequest,
    db: Session = Depends(get_db)
):
    file_record = db.query(File).filter(
        File.file_code == data.code
    ).first()

    if not file_record:

        create_audit_log(
            db=db,
            action="INVALID_FILE_CODE",
            details=f"Invalid file code attempted: {data.code}"
        )

        return {
            "message": "Invalid file code"
        }

    if file_record.expires_at:

        if datetime.now(timezone.utc) > file_record.expires_at:

            create_audit_log(
                db=db,
                action="EXPIRED_FILE_CODE",
                file_id=file_record.id,
                details=f"Expired file code used for '{file_record.filename}'"
            )

            return {
                "message": "File code has expired"
            }

    storage_path = os.path.join(
        "storage",
        file_record.stored_filename
    )

    if not os.path.exists(storage_path):
        return {
            "message": "Encrypted file not found"
        }

    with open(
        storage_path,
        "rb"
    ) as f:
        encrypted_data = f.read()

    decrypted_data = decrypt_file(
        encrypted_data
    )

    create_audit_log(
        db=db,
        action="FILE_DOWNLOAD",
        file_id=file_record.id,
        details=f"File '{file_record.filename}' downloaded using file code"
    )

    return Response(
        content=decrypted_data,
        media_type="application/octet-stream",
        headers={
            "Content-Disposition":
                f'attachment; filename="{file_record.filename}"'
        }
    )
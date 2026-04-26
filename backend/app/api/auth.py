from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
from app.models.database import get_db
from app.models.user import User
from app.schemas.user import LoginRequest, TokenResponse, UserResponse
from app.core.security import verify_password, create_access_token, get_current_user
from app.core.config import settings
from app.utils.logger import log_operation

router = APIRouter(prefix="/api/auth", tags=["认证"])


@router.post("/login", response_model=TokenResponse)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户已被禁用",
        )

    access_token = create_access_token(
        data={"sub": user.id}, expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    log_operation(db, user.id, "login", "users", user.id, {"username": user.username})
    return TokenResponse(
        access_token=access_token,
        user=UserResponse(
            id=user.id,
            username=user.username,
            display_name=user.display_name,
            role=user.role,
            is_active=user.is_active,
            created_at=user.created_at,
        ),
    )


@router.post("/logout")
def logout(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    log_operation(db, current_user["id"], "logout", "users", current_user["id"])
    return {"message": "登出成功"}


@router.get("/me", response_model=UserResponse)
def get_me(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == current_user["id"]).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return UserResponse(
        id=user.id,
        username=user.username,
        display_name=user.display_name,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at,
    )
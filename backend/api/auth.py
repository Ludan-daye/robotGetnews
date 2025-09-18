from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from core.database import get_db
from core.response import success_response
from core.exceptions import BadRequestException, ConflictException, UnauthorizedException
from models.user import User
from api.schemas.auth import (
    UserRegisterRequest,
    UserLoginRequest,
    UserLoginResponse,
    UserResponse,
    UserUpdateRequest,
    TokenValidationResponse
)
from utils.auth import (
    get_password_hash,
    authenticate_user,
    create_access_token,
    get_current_active_user,
    ACCESS_TOKEN_EXPIRE_HOURS
)

router = APIRouter()


@router.post("/register", response_model=UserResponse)
async def register_user(
    user_data: UserRegisterRequest,
    db: Session = Depends(get_db)
):
    """
    Register a new user account
    """
    # Check if user already exists
    existing_user = db.query(User).filter(
        (User.email == user_data.email) | (User.username == user_data.username)
    ).first()

    if existing_user:
        if existing_user.email == user_data.email:
            raise ConflictException("Email already registered")
        else:
            raise ConflictException("Username already taken")

    # Create new user
    hashed_password = get_password_hash(user_data.password)
    new_user = User(
        email=user_data.email,
        username=user_data.username,
        password_hash=hashed_password,
        timezone=user_data.timezone,
        is_active=True,
        email_verified=False
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user


@router.post("/login", response_model=UserLoginResponse)
async def login_user(
    login_data: UserLoginRequest,
    db: Session = Depends(get_db)
):
    """
    Login user and return access token
    """
    user = authenticate_user(db, login_data.email, login_data.password)
    if not user:
        raise UnauthorizedException("Incorrect email or password")

    if not user.is_active:
        raise UnauthorizedException("Account is deactivated")

    # Create access token
    access_token_expires = timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=access_token_expires
    )

    # Update last login time
    from sqlalchemy.sql import func
    user.last_login_at = func.now()
    db.commit()

    return UserLoginResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_HOURS * 3600,  # Convert to seconds
        user=UserResponse.model_validate(user)
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
):
    """
    Get current authenticated user information
    """
    return current_user


@router.post("/logout")
async def logout_user(
    current_user: User = Depends(get_current_active_user)
):
    """
    Logout user (client should discard token)
    """
    return success_response(
        data={"message": "Logged out successfully"},
        message="User logged out"
    )


@router.post("/validate-token", response_model=TokenValidationResponse)
async def validate_token(
    current_user: User = Depends(get_current_active_user)
):
    """
    Validate current token and return user information
    """
    return TokenValidationResponse(
        valid=True,
        user_id=current_user.id,
        expires_at=None  # Could add token expiry if needed
    )


@router.put("/me", response_model=UserResponse)
async def update_user_profile(
    update_data: UserUpdateRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Update current user's profile and notification settings
    """
    # Check if username is being updated and if it's already taken
    if update_data.username and update_data.username != current_user.username:
        existing_user = db.query(User).filter(
            User.username == update_data.username,
            User.id != current_user.id
        ).first()
        if existing_user:
            raise ConflictException("Username already taken")

    # Update user fields if provided
    update_fields = update_data.model_dump(exclude_unset=True)
    for field, value in update_fields.items():
        setattr(current_user, field, value)

    db.commit()
    db.refresh(current_user)

    return current_user
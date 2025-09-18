from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class UserResponse(BaseModel):
    id: int = Field(..., description="User ID")
    email: str = Field(..., description="User email")
    username: Optional[str] = Field(None, description="Username")
    timezone: str = Field(..., description="User timezone")
    is_active: bool = Field(..., description="User account status")
    email_verified: bool = Field(..., description="Email verification status")
    telegram_chat_id: Optional[str] = Field(None, description="Telegram chat ID")
    notification_email: Optional[str] = Field(None, description="Notification email")
    slack_webhook_url: Optional[str] = Field(None, description="Slack webhook URL")
    wechat_webhook_url: Optional[str] = Field(None, description="WeChat webhook URL")
    github_user_id: Optional[str] = Field(None, description="GitHub user ID")

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": 1,
                "email": "user@example.com",
                "username": "johndoe",
                "timezone": "Asia/Singapore",
                "is_active": True,
                "email_verified": True,
                "telegram_chat_id": "123456789",
                "notification_email": None,
                "slack_webhook_url": None,
                "wechat_webhook_url": None,
                "github_user_id": "1234567"
            }
        }
    }


class UserRegisterRequest(BaseModel):
    email: EmailStr = Field(..., description="User email address")
    username: str = Field(..., min_length=3, max_length=50, description="Username (3-50 characters)")
    password: str = Field(..., min_length=8, description="Password (minimum 8 characters)")
    timezone: str = Field(default="Asia/Singapore", description="User timezone")

    model_config = {
        "json_schema_extra": {
            "example": {
                "email": "user@example.com",
                "username": "johndoe",
                "password": "securepassword123",
                "timezone": "Asia/Singapore"
            }
        }
    }


class UserLoginRequest(BaseModel):
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., description="User password")

    model_config = {
        "json_schema_extra": {
            "example": {
                "email": "user@example.com",
                "password": "securepassword123"
            }
        }
    }


class UserLoginResponse(BaseModel):
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration time in seconds")
    user: UserResponse

    model_config = {
        "json_schema_extra": {
            "example": {
                "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                "token_type": "bearer",
                "expires_in": 3600,
                "user": {
                    "id": 1,
                    "email": "user@example.com",
                    "username": "johndoe",
                    "timezone": "Asia/Singapore"
                }
            }
        }
    }


class UserUpdateRequest(BaseModel):
    notification_email: Optional[str] = Field(None, description="Notification email address")
    telegram_chat_id: Optional[str] = Field(None, description="Telegram chat ID")
    slack_webhook_url: Optional[str] = Field(None, description="Slack webhook URL")
    wechat_webhook_url: Optional[str] = Field(None, description="WeChat webhook URL")
    timezone: Optional[str] = Field(None, description="User timezone")
    username: Optional[str] = Field(None, min_length=3, max_length=50, description="Username")

    # SMTP configuration for email notifications
    smtp_host: Optional[str] = Field(None, description="SMTP server host")
    smtp_port: Optional[int] = Field(None, description="SMTP server port")
    smtp_username: Optional[str] = Field(None, description="SMTP username")
    smtp_password: Optional[str] = Field(None, description="SMTP password")
    smtp_use_tls: Optional[bool] = Field(None, description="Use TLS for SMTP")

    model_config = {
        "json_schema_extra": {
            "example": {
                "notification_email": "notifications@example.com",
                "telegram_chat_id": "123456789",
                "slack_webhook_url": "https://hooks.slack.com/services/...",
                "wechat_webhook_url": "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=...",
                "timezone": "Asia/Shanghai",
                "username": "newusername"
            }
        }
    }


class TokenValidationResponse(BaseModel):
    valid: bool = Field(..., description="Whether the token is valid")
    user_id: Optional[int] = Field(None, description="User ID if token is valid")
    expires_at: Optional[str] = Field(None, description="Token expiration time")

    model_config = {
        "json_schema_extra": {
            "example": {
                "valid": True,
                "user_id": 1,
                "expires_at": "2024-12-31T23:59:59Z"
            }
        }
    }
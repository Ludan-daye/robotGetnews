from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), unique=True, index=True, nullable=True)
    password_hash = Column(String(255), nullable=True)  # Nullable for OAuth users
    timezone = Column(String(50), default="Asia/Singapore", nullable=False)

    # Profile/notification settings - embedded for simplicity
    telegram_chat_id = Column(String(100), nullable=True, index=True)
    notification_email = Column(String(255), nullable=True)  # Can differ from login email
    wechat_webhook_url = Column(String(500), nullable=True)
    slack_webhook_url = Column(String(500), nullable=True)

    # Recommendation schedule settings
    recommendation_interval_hours = Column(Integer, default=24, nullable=False)  # Hours between automatic recommendations
    auto_recommendations_enabled = Column(Boolean, default=False, nullable=False)  # Enable/disable automatic recommendations

    # Email SMTP configuration for notifications
    smtp_host = Column(String(255), nullable=True)
    smtp_port = Column(Integer, default=587, nullable=True)
    smtp_username = Column(String(255), nullable=True)
    smtp_password = Column(String(255), nullable=True)  # Encrypted storage recommended
    smtp_use_tls = Column(Boolean, default=True, nullable=True)

    # OAuth integration fields
    github_user_id = Column(String(100), nullable=True, index=True)
    github_access_token = Column(String(255), nullable=True)

    # Status and metadata
    is_active = Column(Boolean, default=True, nullable=False)
    email_verified = Column(Boolean, default=False, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    last_login_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    preferences = relationship("Preference", back_populates="user", cascade="all, delete-orphan")
    recommendations = relationship("Recommendation", back_populates="user", cascade="all, delete-orphan")
    job_runs = relationship("JobRun", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}')>"
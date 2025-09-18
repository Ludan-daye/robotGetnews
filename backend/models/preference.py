from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from core.database import Base


class Preference(Base):
    __tablename__ = "preferences"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Search criteria
    keywords = Column(JSON, default=list, nullable=False)  # ["AI", "machine learning", "web3"]
    languages = Column(JSON, default=list, nullable=False)  # ["Python", "JavaScript", "Go"]
    min_stars = Column(Integer, default=10, nullable=False)
    max_stars = Column(Integer, nullable=True)  # Optional upper limit
    created_after = Column(DateTime(timezone=True), nullable=True)  # Only repos created after this date
    updated_after = Column(DateTime(timezone=True), nullable=True)  # Only repos updated after this date
    excluded_topics = Column(JSON, default=list, nullable=False)  # Topics to exclude
    excluded_keywords = Column(JSON, default=list, nullable=False)  # Keywords to exclude

    # Notification settings
    notification_channels = Column(JSON, default=list, nullable=False)  # ["email", "telegram", "slack"]
    run_cron = Column(String(100), default="0 9 * * *", nullable=False)  # Cron expression for scheduling
    max_recommendations = Column(Integer, default=10, nullable=False)  # Max repos per notification

    # Status
    enabled = Column(Boolean, default=True, nullable=False)

    # Metadata
    name = Column(String(200), nullable=True)  # User-friendly name for this preference set
    description = Column(Text, nullable=True)  # Optional description

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    user = relationship("User", back_populates="preferences")

    def __repr__(self):
        return f"<Preference(id={self.id}, user_id={self.user_id}, enabled={self.enabled})>"
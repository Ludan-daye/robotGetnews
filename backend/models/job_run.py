from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, JSON, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from core.database import Base


class JobRun(Base):
    __tablename__ = "job_runs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Job execution details
    started_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    finished_at = Column(DateTime(timezone=True), nullable=True, index=True)
    status = Column(String(20), default="running", nullable=False, index=True)  # running, completed, failed, cancelled

    # Job statistics and counters
    counters = Column(JSON, default=dict, nullable=False)
    # Example counters structure:
    # {
    #   "repos_fetched": 150,
    #   "repos_filtered": 25,
    #   "recommendations_generated": 10,
    #   "notifications_sent": 8,
    #   "errors_count": 0
    # }

    # Error tracking
    error_message = Column(Text, nullable=True)
    error_details = Column(JSON, default=dict, nullable=True)

    # Job configuration snapshot
    job_config = Column(JSON, default=dict, nullable=False)  # Snapshot of user preferences at job time
    trigger_type = Column(String(20), default="scheduled", nullable=False)  # scheduled, manual, webhook

    # Job metadata
    preference_id = Column(Integer, ForeignKey("preferences.id", ondelete="SET NULL"), nullable=True, index=True)
    external_job_id = Column(String(100), nullable=True, index=True)  # For external scheduler integration

    # Duration tracking
    @property
    def duration_seconds(self):
        if self.finished_at and self.started_at:
            return (self.finished_at - self.started_at).total_seconds()
        return None

    # Relationships
    user = relationship("User", back_populates="job_runs")
    preference = relationship("Preference")
    recommendations = relationship("Recommendation", back_populates="job_run", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<JobRun(id={self.id}, user_id={self.user_id}, status='{self.status}')>"


# Performance indexes
Index('idx_job_runs_status_started', JobRun.status, JobRun.started_at)
Index('idx_job_runs_user_status', JobRun.user_id, JobRun.status)
Index('idx_job_runs_trigger_type', JobRun.trigger_type, JobRun.started_at)
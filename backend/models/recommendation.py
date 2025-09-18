from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float, Text, JSON, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from core.database import Base


class Recommendation(Base):
    __tablename__ = "recommendations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    repo_id = Column(Integer, ForeignKey("repo_cache.repo_id", ondelete="CASCADE"), nullable=False, index=True)

    # Recommendation scoring and reasoning
    score = Column(Float, default=0.0, nullable=False, index=True)  # 0.0 - 1.0 relevance score
    reason = Column(JSON, default=dict, nullable=False)  # Which rules/keywords matched

    # Example reason structure:
    # {
    #   "matched_keywords": ["AI", "machine learning"],
    #   "language_match": "Python",
    #   "star_score": 0.8,
    #   "freshness_score": 0.6,
    #   "total_score": 0.75
    # }

    # Notification tracking
    sent_channels = Column(JSON, default=list, nullable=False)  # ["email", "telegram"]
    sent_at = Column(DateTime(timezone=True), nullable=True, index=True)

    # Status and metadata
    preference_id = Column(Integer, ForeignKey("preferences.id", ondelete="CASCADE"), nullable=True, index=True)
    job_run_id = Column(Integer, ForeignKey("job_runs.id", ondelete="SET NULL"), nullable=True, index=True)

    # Additional context
    recommendation_context = Column(JSON, default=dict, nullable=False)  # Additional metadata

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    # Relationships
    user = relationship("User", back_populates="recommendations")
    preference = relationship("Preference")
    job_run = relationship("JobRun", back_populates="recommendations")

    def __repr__(self):
        return f"<Recommendation(id={self.id}, user_id={self.user_id}, repo_id={self.repo_id}, score={self.score})>"


# Prevent duplicate recommendations for same user+repo combination
Index('idx_recommendations_user_repo_unique', Recommendation.user_id, Recommendation.repo_id, unique=True)
Index('idx_recommendations_score_created', Recommendation.score, Recommendation.created_at)
Index('idx_recommendations_sent_at', Recommendation.sent_at)
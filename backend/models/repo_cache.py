from sqlalchemy import Column, Integer, String, DateTime, Text, Index, JSON
from sqlalchemy.sql import func
from core.database import Base


class RepoCache(Base):
    __tablename__ = "repo_cache"

    id = Column(Integer, primary_key=True, index=True)
    repo_id = Column(Integer, unique=True, nullable=False, index=True)  # GitHub repository ID
    full_name = Column(String(255), nullable=False, index=True)  # "owner/repo"
    name = Column(String(255), nullable=False)  # Repository name
    owner_login = Column(String(100), nullable=False, index=True)  # Repository owner

    # Repository details
    description = Column(Text, nullable=True)
    topics = Column(JSON, default=list, nullable=False)  # Repository topics/tags
    language = Column(String(50), nullable=True, index=True)  # Primary language
    license_name = Column(String(100), nullable=True)  # License (MIT, Apache, etc.)

    # GitHub metrics
    stargazers_count = Column(Integer, default=0, nullable=False, index=True)
    forks_count = Column(Integer, default=0, nullable=False)
    watchers_count = Column(Integer, default=0, nullable=False)
    open_issues_count = Column(Integer, default=0, nullable=False)
    size = Column(Integer, default=0, nullable=False)  # Repository size in KB

    # URLs and links
    html_url = Column(String(500), nullable=False)  # GitHub page URL
    clone_url = Column(String(500), nullable=False)  # Git clone URL
    homepage = Column(String(500), nullable=True)  # Project homepage

    # Repository status
    is_private = Column(String(10), default="false", nullable=False)  # "true"/"false" as string
    is_fork = Column(String(10), default="false", nullable=False)
    is_archived = Column(String(10), default="false", nullable=False)
    is_disabled = Column(String(10), default="false", nullable=False)

    # Timestamps from GitHub
    created_at = Column(DateTime(timezone=True), nullable=False)  # When repo was created on GitHub
    updated_at = Column(DateTime(timezone=True), nullable=False)  # Last updated on GitHub
    pushed_at = Column(DateTime(timezone=True), nullable=True)  # Last push to default branch

    # Cache metadata
    fetched_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    # Additional data for future use
    github_data = Column(JSON, nullable=True)  # Store additional GitHub API response data

    def __repr__(self):
        return f"<RepoCache(id={self.id}, full_name='{self.full_name}', stars={self.stargazers_count})>"


# Create indexes for performance
Index('idx_repo_cache_fetched_at', RepoCache.fetched_at)
Index('idx_repo_cache_stars_updated', RepoCache.stargazers_count, RepoCache.updated_at)
Index('idx_repo_cache_language_stars', RepoCache.language, RepoCache.stargazers_count)
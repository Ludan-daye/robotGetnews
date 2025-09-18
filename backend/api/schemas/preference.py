from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class PreferenceRequest(BaseModel):
    name: Optional[str] = Field(None, max_length=200, description="Preference set name")
    description: Optional[str] = Field(None, description="Preference description")
    keywords: List[str] = Field(default_factory=list, description="Keywords to search for")
    languages: List[str] = Field(default_factory=list, description="Programming languages to filter")
    min_stars: int = Field(default=10, ge=0, description="Minimum number of stars")
    max_stars: Optional[int] = Field(None, ge=0, description="Maximum number of stars")
    created_after: Optional[datetime] = Field(None, description="Only repos created after this date")
    updated_after: Optional[datetime] = Field(None, description="Only repos updated after this date")
    excluded_topics: List[str] = Field(default_factory=list, description="Topics to exclude")
    excluded_keywords: List[str] = Field(default_factory=list, description="Keywords to exclude")
    notification_channels: List[str] = Field(default_factory=list, description="Notification channels")
    run_cron: str = Field(default="0 9 * * *", description="Cron expression for scheduling")
    max_recommendations: int = Field(default=10, ge=1, le=50, description="Max recommendations per run")
    enabled: bool = Field(default=True, description="Whether this preference is active")

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "AI & Machine Learning",
                "description": "Repositories related to AI and machine learning",
                "keywords": ["artificial intelligence", "machine learning", "neural network"],
                "languages": ["Python", "JavaScript", "Go"],
                "min_stars": 50,
                "max_stars": None,
                "created_after": "2024-01-01T00:00:00Z",
                "updated_after": None,
                "excluded_topics": ["tutorial", "example"],
                "excluded_keywords": ["deprecated"],
                "notification_channels": ["email", "telegram"],
                "run_cron": "0 9 * * *",
                "max_recommendations": 10,
                "enabled": True
            }
        }
    }


class PreferenceResponse(BaseModel):
    id: int = Field(..., description="Preference ID")
    user_id: int = Field(..., description="User ID")
    name: Optional[str] = Field(None, description="Preference set name")
    description: Optional[str] = Field(None, description="Preference description")
    keywords: List[str] = Field(..., description="Keywords to search for")
    languages: List[str] = Field(..., description="Programming languages to filter")
    min_stars: int = Field(..., description="Minimum number of stars")
    max_stars: Optional[int] = Field(None, description="Maximum number of stars")
    created_after: Optional[datetime] = Field(None, description="Only repos created after this date")
    updated_after: Optional[datetime] = Field(None, description="Only repos updated after this date")
    excluded_topics: List[str] = Field(..., description="Topics to exclude")
    excluded_keywords: List[str] = Field(..., description="Keywords to exclude")
    notification_channels: List[str] = Field(..., description="Notification channels")
    run_cron: str = Field(..., description="Cron expression for scheduling")
    max_recommendations: int = Field(..., description="Max recommendations per run")
    enabled: bool = Field(..., description="Whether this preference is active")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": 1,
                "user_id": 1,
                "name": "AI & Machine Learning",
                "description": "Repositories related to AI and machine learning",
                "keywords": ["artificial intelligence", "machine learning"],
                "languages": ["Python", "JavaScript"],
                "min_stars": 50,
                "max_stars": None,
                "created_after": "2024-01-01T00:00:00Z",
                "updated_after": None,
                "excluded_topics": ["tutorial"],
                "excluded_keywords": ["deprecated"],
                "notification_channels": ["email", "telegram"],
                "run_cron": "0 9 * * *",
                "max_recommendations": 10,
                "enabled": True,
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-15T10:30:00Z"
            }
        }
    }
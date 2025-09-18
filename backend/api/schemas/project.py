from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, HttpUrl


class RepoResponse(BaseModel):
    id: int = Field(..., description="Repository ID")
    repo_id: int = Field(..., description="GitHub repository ID")
    full_name: str = Field(..., description="Repository full name (owner/repo)")
    name: str = Field(..., description="Repository name")
    owner_login: str = Field(..., description="Repository owner")
    description: Optional[str] = Field(None, description="Repository description")
    topics: List[str] = Field(..., description="Repository topics/tags")
    language: Optional[str] = Field(None, description="Primary programming language")
    license_name: Optional[str] = Field(None, description="License name")
    stargazers_count: int = Field(..., description="Number of stars")
    forks_count: int = Field(..., description="Number of forks")
    watchers_count: int = Field(..., description="Number of watchers")
    open_issues_count: int = Field(..., description="Number of open issues")
    html_url: str = Field(..., description="GitHub page URL")
    homepage: Optional[str] = Field(None, description="Project homepage")
    created_at: datetime = Field(..., description="Repository creation date")
    updated_at: datetime = Field(..., description="Last updated date")
    pushed_at: Optional[datetime] = Field(None, description="Last push date")

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": 1,
                "repo_id": 123456789,
                "full_name": "openai/gpt-4",
                "name": "gpt-4",
                "owner_login": "openai",
                "description": "GPT-4 implementation",
                "topics": ["ai", "machine-learning", "gpt"],
                "language": "Python",
                "license_name": "MIT",
                "stargazers_count": 15000,
                "forks_count": 2500,
                "watchers_count": 1200,
                "open_issues_count": 45,
                "html_url": "https://github.com/openai/gpt-4",
                "homepage": "https://openai.com/gpt-4",
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-15T12:00:00Z",
                "pushed_at": "2024-01-15T11:30:00Z"
            }
        }
    }


class RecommendationResponse(BaseModel):
    id: int = Field(..., description="Recommendation ID")
    repo: RepoResponse = Field(..., description="Recommended repository")
    score: float = Field(..., description="Recommendation score (0.0-1.0)")
    reason: Dict[str, Any] = Field(..., description="Recommendation reasoning")
    sent_channels: List[str] = Field(..., description="Channels where notification was sent")
    sent_at: Optional[datetime] = Field(None, description="When notification was sent")
    created_at: datetime = Field(..., description="Recommendation creation time")

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": 1,
                "repo": {
                    "id": 1,
                    "repo_id": 123456789,
                    "full_name": "openai/gpt-4",
                    "name": "gpt-4",
                    "owner_login": "openai",
                    "description": "GPT-4 implementation",
                    "topics": ["ai", "machine-learning"],
                    "language": "Python",
                    "stargazers_count": 15000,
                    "html_url": "https://github.com/openai/gpt-4"
                },
                "score": 0.85,
                "reason": {
                    "matched_keywords": ["ai", "machine learning"],
                    "language_match": "Python",
                    "star_score": 0.9,
                    "freshness_score": 0.8
                },
                "sent_channels": ["email", "telegram"],
                "sent_at": "2024-01-15T09:00:00Z",
                "created_at": "2024-01-15T08:30:00Z"
            }
        }
    }


class TriggerRunRequest(BaseModel):
    preference_id: Optional[int] = Field(None, description="Specific preference to run (all if not specified)")
    force_refresh: bool = Field(default=False, description="Force refresh cache from GitHub")

    model_config = {
        "json_schema_extra": {
            "example": {
                "preference_id": 1,
                "force_refresh": False
            }
        }
    }


class TriggerRunResponse(BaseModel):
    job_run_id: int = Field(..., description="Job run ID")
    status: str = Field(..., description="Job status")
    message: str = Field(..., description="Status message")

    model_config = {
        "json_schema_extra": {
            "example": {
                "job_run_id": 123,
                "status": "started",
                "message": "Recommendation job started successfully"
            }
        }
    }


class HistoryFilter(BaseModel):
    page: int = Field(default=1, ge=1, description="Page number")
    page_size: int = Field(default=20, ge=1, le=100, description="Items per page")
    keyword: Optional[str] = Field(None, description="Filter by keyword in repo name/description")
    language: Optional[str] = Field(None, description="Filter by programming language")
    min_stars: Optional[int] = Field(None, ge=0, description="Minimum stars filter")
    date_from: Optional[datetime] = Field(None, description="Filter recommendations from this date")
    date_to: Optional[datetime] = Field(None, description="Filter recommendations to this date")

    model_config = {
        "json_schema_extra": {
            "example": {
                "page": 1,
                "page_size": 20,
                "keyword": "machine learning",
                "language": "Python",
                "min_stars": 100,
                "date_from": "2024-01-01T00:00:00Z",
                "date_to": "2024-01-31T23:59:59Z"
            }
        }
    }


class HistoryResponse(BaseModel):
    items: List[RecommendationResponse] = Field(..., description="Recommendation items")
    total: int = Field(..., description="Total number of items")
    page: int = Field(..., description="Current page")
    page_size: int = Field(..., description="Items per page")
    total_pages: int = Field(..., description="Total number of pages")

    model_config = {
        "json_schema_extra": {
            "example": {
                "items": [],
                "total": 150,
                "page": 1,
                "page_size": 20,
                "total_pages": 8
            }
        }
    }


class ChannelStatus(BaseModel):
    channel: str = Field(..., description="Channel name")
    available: bool = Field(..., description="Whether channel is available/configured")
    last_used: Optional[datetime] = Field(None, description="Last time channel was used")
    error_message: Optional[str] = Field(None, description="Error message if unavailable")

    model_config = {
        "json_schema_extra": {
            "example": {
                "channel": "email",
                "available": True,
                "last_used": "2024-01-15T09:00:00Z",
                "error_message": None
            }
        }
    }


class ChannelsResponse(BaseModel):
    channels: List[ChannelStatus] = Field(..., description="Available notification channels")

    model_config = {
        "json_schema_extra": {
            "example": {
                "channels": [
                    {
                        "channel": "email",
                        "available": True,
                        "last_used": "2024-01-15T09:00:00Z",
                        "error_message": None
                    },
                    {
                        "channel": "telegram",
                        "available": False,
                        "last_used": None,
                        "error_message": "Telegram chat ID not configured"
                    }
                ]
            }
        }
    }


class EmailTestRequest(BaseModel):
    to_email: str = Field(..., description="Test email recipient")
    smtp_host: str = Field(..., description="SMTP server host")
    smtp_port: int = Field(587, description="SMTP server port")
    smtp_username: str = Field(..., description="SMTP username")
    smtp_password: str = Field(..., description="SMTP password")
    use_tls: bool = Field(True, description="Whether to use TLS")

    model_config = {
        "json_schema_extra": {
            "example": {
                "to_email": "user@example.com",
                "smtp_host": "smtp.gmail.com",
                "smtp_port": 587,
                "smtp_username": "your-email@gmail.com",
                "smtp_password": "your-app-password",
                "use_tls": True
            }
        }
    }


class EmailTestResponse(BaseModel):
    success: bool = Field(..., description="Whether email was sent successfully")
    message: str = Field(..., description="Result message")

    model_config = {
        "json_schema_extra": {
            "example": {
                "success": True,
                "message": "Test email sent successfully"
            }
        }
    }


class TelegramTestRequest(BaseModel):
    bot_token: str = Field(..., description="Telegram Bot Token")
    chat_id: str = Field(..., description="Telegram Chat ID")

    model_config = {
        "json_schema_extra": {
            "example": {
                "bot_token": "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11",
                "chat_id": "123456789"
            }
        }
    }


class SlackTestRequest(BaseModel):
    webhook_url: str = Field(..., description="Slack Webhook URL")

    model_config = {
        "json_schema_extra": {
            "example": {
                "webhook_url": "https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX"
            }
        }
    }


class WechatTestRequest(BaseModel):
    webhook_url: str = Field(..., description="WeChat Work Webhook URL")

    model_config = {
        "json_schema_extra": {
            "example": {
                "webhook_url": "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
            }
        }
    }


class NotificationTestResponse(BaseModel):
    success: bool = Field(..., description="Whether notification was sent successfully")
    message: str = Field(..., description="Result message")

    model_config = {
        "json_schema_extra": {
            "example": {
                "success": True,
                "message": "Test notification sent successfully"
            }
        }
    }
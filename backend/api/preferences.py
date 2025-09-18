from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from core.database import get_db
from core.response import success_response
from core.exceptions import NotFoundException, BadRequestException
from models.user import User
from models.preference import Preference
from api.schemas.preference import PreferenceRequest, PreferenceResponse
from utils.auth import get_current_active_user

router = APIRouter()


@router.get("", response_model=List[PreferenceResponse])
async def get_user_preferences(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get all preferences for the current user
    """
    preferences = db.query(Preference).filter(
        Preference.user_id == current_user.id
    ).order_by(Preference.created_at.desc()).all()

    return preferences


@router.get("/{preference_id}", response_model=PreferenceResponse)
async def get_preference(
    preference_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get a specific preference by ID
    """
    preference = db.query(Preference).filter(
        Preference.id == preference_id,
        Preference.user_id == current_user.id
    ).first()

    if not preference:
        raise NotFoundException("Preference not found")

    return preference


@router.post("", response_model=PreferenceResponse, status_code=status.HTTP_201_CREATED)
async def create_preference(
    preference_data: PreferenceRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Create a new preference for the current user
    """
    # Validate cron expression (basic validation)
    if preference_data.run_cron and not _is_valid_cron(preference_data.run_cron):
        raise BadRequestException("Invalid cron expression")

    # Validate notification channels
    valid_channels = {"email", "telegram", "slack", "wechat"}
    invalid_channels = set(preference_data.notification_channels) - valid_channels
    if invalid_channels:
        raise BadRequestException(f"Invalid notification channels: {', '.join(invalid_channels)}")

    new_preference = Preference(
        user_id=current_user.id,
        name=preference_data.name,
        description=preference_data.description,
        keywords=preference_data.keywords,
        languages=preference_data.languages,
        min_stars=preference_data.min_stars,
        max_stars=preference_data.max_stars,
        created_after=preference_data.created_after,
        updated_after=preference_data.updated_after,
        excluded_topics=preference_data.excluded_topics,
        excluded_keywords=preference_data.excluded_keywords,
        notification_channels=preference_data.notification_channels,
        run_cron=preference_data.run_cron,
        max_recommendations=preference_data.max_recommendations,
        enabled=preference_data.enabled
    )

    db.add(new_preference)
    db.commit()
    db.refresh(new_preference)

    return new_preference


@router.put("/{preference_id}", response_model=PreferenceResponse)
async def update_preference(
    preference_id: int,
    preference_data: PreferenceRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Update an existing preference
    """
    preference = db.query(Preference).filter(
        Preference.id == preference_id,
        Preference.user_id == current_user.id
    ).first()

    if not preference:
        raise NotFoundException("Preference not found")

    # Validate cron expression
    if preference_data.run_cron and not _is_valid_cron(preference_data.run_cron):
        raise BadRequestException("Invalid cron expression")

    # Validate notification channels
    valid_channels = {"email", "telegram", "slack", "wechat"}
    invalid_channels = set(preference_data.notification_channels) - valid_channels
    if invalid_channels:
        raise BadRequestException(f"Invalid notification channels: {', '.join(invalid_channels)}")

    # Update preference fields
    for field, value in preference_data.model_dump(exclude_unset=True).items():
        setattr(preference, field, value)

    db.commit()
    db.refresh(preference)

    return preference


@router.delete("/{preference_id}")
async def delete_preference(
    preference_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Delete a preference
    """
    preference = db.query(Preference).filter(
        Preference.id == preference_id,
        Preference.user_id == current_user.id
    ).first()

    if not preference:
        raise NotFoundException("Preference not found")

    db.delete(preference)
    db.commit()

    return success_response(
        data={"deleted": True},
        message="Preference deleted successfully"
    )


@router.patch("/{preference_id}/toggle")
async def toggle_preference(
    preference_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Toggle preference enabled/disabled status
    """
    preference = db.query(Preference).filter(
        Preference.id == preference_id,
        Preference.user_id == current_user.id
    ).first()

    if not preference:
        raise NotFoundException("Preference not found")

    preference.enabled = not preference.enabled
    db.commit()

    return success_response(
        data={"enabled": preference.enabled},
        message=f"Preference {'enabled' if preference.enabled else 'disabled'}"
    )


def _is_valid_cron(cron_expression: str) -> bool:
    """
    Basic cron expression validation
    Should be in format: "minute hour day month weekday"
    """
    parts = cron_expression.strip().split()
    return len(parts) == 5
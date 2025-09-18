from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, and_, or_
from core.database import get_db
from core.response import success_response
from core.exceptions import NotFoundException, BadRequestException
from models.user import User
from models.recommendation import Recommendation
from models.repo_cache import RepoCache
from models.job_run import JobRun
from api.schemas.project import (
    RecommendationResponse,
    TriggerRunRequest,
    TriggerRunResponse,
    HistoryResponse,
    EmailTestRequest,
    EmailTestResponse,
    TelegramTestRequest,
    SlackTestRequest,
    WechatTestRequest,
    NotificationTestResponse
)
from utils.auth import get_current_active_user

router = APIRouter()


@router.get("/latest", response_model=List[RecommendationResponse])
async def get_latest_recommendations(
    limit: int = Query(default=10, ge=1, le=50, description="Number of recommendations to return"),
    db: Session = Depends(get_db)
):
    """
    Get latest recommendations (public access)
    """
    recommendations = (
        db.query(Recommendation)
        .join(RepoCache, Recommendation.repo_id == RepoCache.repo_id)
        .order_by(desc(Recommendation.created_at))
        .limit(limit)
        .all()
    )

    # Convert to response format with repo data
    result = []
    for rec in recommendations:
        repo = db.query(RepoCache).filter(RepoCache.repo_id == rec.repo_id).first()
        if repo:
            result.append({
                "id": rec.id,
                "repo": repo,
                "score": rec.score,
                "reason": rec.reason,
                "sent_channels": rec.sent_channels,
                "sent_at": rec.sent_at,
                "created_at": rec.created_at
            })

    return result


@router.get("/my/latest", response_model=List[RecommendationResponse])
async def get_my_latest_recommendations(
    limit: int = Query(default=10, ge=1, le=50, description="Number of recommendations to return"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get latest recommendations for the current user (requires authentication)
    """
    recommendations = (
        db.query(Recommendation)
        .join(RepoCache, Recommendation.repo_id == RepoCache.repo_id)
        .filter(Recommendation.user_id == current_user.id)
        .order_by(desc(Recommendation.created_at))
        .limit(limit)
        .all()
    )

    # Convert to response format with repo data
    result = []
    for rec in recommendations:
        repo = db.query(RepoCache).filter(RepoCache.repo_id == rec.repo_id).first()
        if repo:
            result.append({
                "id": rec.id,
                "repo": repo,
                "score": rec.score,
                "reason": rec.reason,
                "sent_channels": rec.sent_channels,
                "sent_at": rec.sent_at,
                "created_at": rec.created_at
            })

    return result


@router.post("/runs/trigger", response_model=TriggerRunResponse)
async def trigger_recommendation_run(
    request: TriggerRunRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Manually trigger a recommendation job
    """
    from services.job_service import JobExecutionService
    import asyncio

    # Create a new job run record
    job_run = JobRun(
        user_id=current_user.id,
        status="queued",
        trigger_type="manual",
        preference_id=request.preference_id,
        job_config={
            "force_refresh": request.force_refresh,
            "preference_id": request.preference_id
        }
    )

    db.add(job_run)
    db.commit()
    db.refresh(job_run)

    # Execute the job asynchronously
    try:
        job_service = JobExecutionService(db)
        result = await job_service.execute_recommendation_job(
            user_id=current_user.id,
            job_run_id=job_run.id,
            preference_id=request.preference_id,
            force_refresh=request.force_refresh
        )

        return TriggerRunResponse(
            job_run_id=job_run.id,
            status=result["status"],
            message=f"Job completed successfully. Generated {result.get('stats', {}).get('recommendations_generated', 0)} recommendations."
        )

    except Exception as e:
        return TriggerRunResponse(
            job_run_id=job_run.id,
            status="failed",
            message=f"Job failed: {str(e)}"
        )


@router.get("/history", response_model=HistoryResponse)
async def get_recommendation_history(
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    keyword: Optional[str] = Query(None, description="Filter by keyword in repo name/description"),
    language: Optional[str] = Query(None, description="Filter by programming language"),
    min_stars: Optional[int] = Query(None, ge=0, description="Minimum stars filter"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get paginated recommendation history with optional filters
    """
    # Build query
    query = (
        db.query(Recommendation)
        .join(RepoCache, Recommendation.repo_id == RepoCache.repo_id)
        .filter(Recommendation.user_id == current_user.id)
    )

    # Apply filters
    if keyword:
        keyword_filter = or_(
            RepoCache.full_name.ilike(f"%{keyword}%"),
            RepoCache.description.ilike(f"%{keyword}%")
        )
        query = query.filter(keyword_filter)

    if language:
        query = query.filter(RepoCache.language == language)

    if min_stars:
        query = query.filter(RepoCache.stargazers_count >= min_stars)

    # Get total count
    total = query.count()

    # Apply pagination
    offset = (page - 1) * page_size
    recommendations = (
        query.order_by(desc(Recommendation.created_at))
        .offset(offset)
        .limit(page_size)
        .all()
    )

    # Convert to response format
    items = []
    for rec in recommendations:
        repo = db.query(RepoCache).filter(RepoCache.repo_id == rec.repo_id).first()
        if repo:
            items.append({
                "id": rec.id,
                "repo": repo,
                "score": rec.score,
                "reason": rec.reason,
                "sent_channels": rec.sent_channels,
                "sent_at": rec.sent_at,
                "created_at": rec.created_at
            })

    total_pages = (total + page_size - 1) // page_size

    return HistoryResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )




@router.get("/runs/status/{job_run_id}")
async def get_job_run_status(
    job_run_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get status of a specific job run
    """
    job_run = db.query(JobRun).filter(
        JobRun.id == job_run_id,
        JobRun.user_id == current_user.id
    ).first()

    if not job_run:
        raise NotFoundException("Job run not found")

    return success_response(
        data={
            "id": job_run.id,
            "status": job_run.status,
            "started_at": job_run.started_at,
            "finished_at": job_run.finished_at,
            "counters": job_run.counters,
            "error_message": job_run.error_message,
            "duration_seconds": job_run.duration_seconds
        },
        message="Job run status retrieved"
    )


@router.post("/test/email", response_model=EmailTestResponse)
async def test_email_notification(
    email_test: EmailTestRequest,
    current_user: User = Depends(get_current_active_user)
):
    """
    Test email notification with provided settings
    """
    from utils.email import send_test_email

    try:
        success = await send_test_email(
            to_email=email_test.to_email,
            smtp_host=email_test.smtp_host,
            smtp_port=email_test.smtp_port,
            smtp_username=email_test.smtp_username,
            smtp_password=email_test.smtp_password,
            use_tls=email_test.use_tls
        )

        if success:
            return EmailTestResponse(
                success=True,
                message="测试邮件发送成功！请检查您的邮箱。"
            )
        else:
            return EmailTestResponse(
                success=False,
                message="测试邮件发送失败，请检查SMTP设置。"
            )

    except Exception as e:
        return EmailTestResponse(
            success=False,
            message=f"测试邮件发送失败：{str(e)}"
        )


@router.post("/test/telegram", response_model=NotificationTestResponse)
async def test_telegram_notification(
    telegram_test: TelegramTestRequest,
    current_user: User = Depends(get_current_active_user)
):
    """
    Test Telegram notification with provided settings
    """
    from utils.notifications import send_test_telegram

    try:
        success = await send_test_telegram(
            bot_token=telegram_test.bot_token,
            chat_id=telegram_test.chat_id
        )

        if success:
            return NotificationTestResponse(
                success=True,
                message="Telegram测试消息发送成功！请检查您的Telegram。"
            )
        else:
            return NotificationTestResponse(
                success=False,
                message="Telegram测试消息发送失败，请检查Bot Token和Chat ID。"
            )

    except Exception as e:
        return NotificationTestResponse(
            success=False,
            message=f"Telegram测试消息发送失败：{str(e)}"
        )


@router.post("/test/slack", response_model=NotificationTestResponse)
async def test_slack_notification(
    slack_test: SlackTestRequest,
    current_user: User = Depends(get_current_active_user)
):
    """
    Test Slack notification with provided settings
    """
    from utils.notifications import send_test_slack

    try:
        success = await send_test_slack(
            webhook_url=slack_test.webhook_url
        )

        if success:
            return NotificationTestResponse(
                success=True,
                message="Slack测试消息发送成功！请检查您的Slack频道。"
            )
        else:
            return NotificationTestResponse(
                success=False,
                message="Slack测试消息发送失败，请检查Webhook URL。"
            )

    except Exception as e:
        return NotificationTestResponse(
            success=False,
            message=f"Slack测试消息发送失败：{str(e)}"
        )


@router.post("/test/wechat", response_model=NotificationTestResponse)
async def test_wechat_notification(
    wechat_test: WechatTestRequest,
    current_user: User = Depends(get_current_active_user)
):
    """
    Test WeChat Work notification with provided settings
    """
    from utils.notifications import send_test_wechat

    try:
        success = await send_test_wechat(
            webhook_url=wechat_test.webhook_url
        )

        if success:
            return NotificationTestResponse(
                success=True,
                message="企业微信测试消息发送成功！请检查您的企业微信群。"
            )
        else:
            return NotificationTestResponse(
                success=False,
                message="企业微信测试消息发送失败，请检查Webhook URL。"
            )

    except Exception as e:
        return NotificationTestResponse(
            success=False,
            message=f"企业微信测试消息发送失败：{str(e)}"
        )
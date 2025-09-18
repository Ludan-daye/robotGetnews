import asyncio
from typing import List, Dict, Any
import structlog
from sqlalchemy.orm import Session
from datetime import datetime

from models.user import User
from models.preference import Preference
from models.recommendation import Recommendation
from models.repo_cache import RepoCache
from utils.notifications import send_telegram_message, send_slack_message, send_wechat_message
from utils.email import send_email

logger = structlog.get_logger()


class NotificationService:
    """推荐通知服务"""

    def __init__(self, db: Session):
        self.db = db

    async def send_recommendations_notification(
        self,
        user_id: int,
        preference: Preference,
        recommendations: List[Recommendation]
    ) -> List[str]:
        """
        为用户发送推荐通知

        Args:
            user_id: 用户ID
            preference: 偏好设置
            recommendations: 推荐列表

        Returns:
            List[str]: 成功发送的通知渠道列表
        """
        if not recommendations:
            logger.info("No recommendations to send", user_id=user_id, preference_id=preference.id)
            return []

        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            logger.error("User not found", user_id=user_id)
            return []

        sent_channels = []

        # 准备通知内容
        notification_content = await self._prepare_notification_content(recommendations, preference)

        # 发送邮件通知
        if "email" in preference.notification_channels and user.notification_email:
            try:
                success = await self._send_email_notification(
                    user.notification_email,
                    notification_content
                )
                if success:
                    sent_channels.append("email")
                    logger.info("Email notification sent", user_id=user_id, email=user.notification_email)
            except Exception as e:
                logger.error("Failed to send email notification", user_id=user_id, error=str(e))

        # 发送Telegram通知
        if "telegram" in preference.notification_channels and user.telegram_chat_id:
            try:
                success = await self._send_telegram_notification(
                    user.telegram_chat_id,
                    notification_content
                )
                if success:
                    sent_channels.append("telegram")
                    logger.info("Telegram notification sent", user_id=user_id, chat_id=user.telegram_chat_id)
            except Exception as e:
                logger.error("Failed to send Telegram notification", user_id=user_id, error=str(e))

        # 发送Slack通知
        if "slack" in preference.notification_channels and user.slack_webhook_url:
            try:
                success = await self._send_slack_notification(
                    user.slack_webhook_url,
                    notification_content
                )
                if success:
                    sent_channels.append("slack")
                    logger.info("Slack notification sent", user_id=user_id)
            except Exception as e:
                logger.error("Failed to send Slack notification", user_id=user_id, error=str(e))

        # 发送微信通知
        if "wechat" in preference.notification_channels and user.wechat_webhook_url:
            try:
                success = await self._send_wechat_notification(
                    user.wechat_webhook_url,
                    notification_content
                )
                if success:
                    sent_channels.append("wechat")
                    logger.info("WeChat notification sent", user_id=user_id)
            except Exception as e:
                logger.error("Failed to send WeChat notification", user_id=user_id, error=str(e))

        # 更新推荐记录的通知状态
        await self._update_recommendations_notification_status(recommendations, sent_channels)

        logger.info(
            "Notifications sent",
            user_id=user_id,
            preference_id=preference.id,
            sent_channels=sent_channels,
            recommendations_count=len(recommendations)
        )

        return sent_channels

    async def _prepare_notification_content(
        self,
        recommendations: List[Recommendation],
        preference: Preference
    ) -> Dict[str, Any]:
        """准备通知内容"""

        # 获取推荐的仓库信息
        repo_data = []
        for rec in recommendations:
            repo = self.db.query(RepoCache).filter(RepoCache.repo_id == rec.repo_id).first()
            if repo:
                repo_data.append({
                    "name": repo.full_name,
                    "description": repo.description or "No description",
                    "stars": repo.stargazers_count,
                    "url": repo.html_url,
                    "language": repo.language,
                    "score": rec.score,
                    "reason": rec.reason
                })

        return {
            "preference_name": preference.name,
            "repositories": repo_data,
            "total_count": len(repo_data)
        }

    async def _send_email_notification(self, email: str, content: Dict[str, Any]) -> bool:
        """发送邮件通知"""
        try:
            subject = f"🚀 GitHub推荐: {content['preference_name']} - {content['total_count']}个新项目"

            # 构建邮件内容
            html_body = f"""
            <h2>🚀 GitHub项目推荐</h2>
            <p>根据您的偏好 "<strong>{content['preference_name']}</strong>"，我们为您推荐了 {content['total_count']} 个项目：</p>
            <br>
            """

            for i, repo in enumerate(content['repositories'], 1):
                html_body += f"""
                <div style="border: 1px solid #ddd; padding: 15px; margin: 10px 0; border-radius: 5px;">
                    <h3>{i}. <a href="{repo['url']}" target="_blank">{repo['name']}</a></h3>
                    <p><strong>⭐ Stars:</strong> {repo['stars']:,} | <strong>💻 Language:</strong> {repo['language'] or 'N/A'}</p>
                    <p><strong>📝 Description:</strong> {repo['description'][:200]}{'...' if len(repo['description']) > 200 else ''}</p>
                    <p><strong>🎯 推荐评分:</strong> {repo['score']:.2f}</p>
                    {('<p><strong>📋 推荐理由:</strong> ' + str(repo['reason']) + '</p>') if repo['reason'] else ''}
                </div>
                """

            html_body += """
            <br>
            <p style="color: #666; font-size: 12px;">
                此邮件由GitHub Bot自动发送。如不需要接收推荐，请在设置中修改通知偏好。
            </p>
            """

            # 获取用户的SMTP配置
            user = self.db.query(User).filter(User.notification_email == email).first()
            if not user or not user.smtp_host or not user.smtp_username or not user.smtp_password:
                logger.error("User SMTP configuration not found or incomplete", email=email)
                return False

            # 使用用户的SMTP配置发送邮件
            success = await send_email(
                to_email=email,
                subject=subject,
                content=html_body,
                smtp_host=user.smtp_host,
                smtp_port=user.smtp_port or 587,
                smtp_username=user.smtp_username,
                smtp_password=user.smtp_password,
                use_tls=user.smtp_use_tls if user.smtp_use_tls is not None else True
            )
            logger.info("Email notification sent", email=email, subject=subject, success=success)
            return success

        except Exception as e:
            logger.error("Error preparing email notification", error=str(e))
            return False

    async def _send_telegram_notification(self, chat_id: str, content: Dict[str, Any]) -> bool:
        """发送Telegram通知"""
        try:
            message = f"🚀 *GitHub项目推荐*\n\n"
            message += f"根据您的偏好 \"*{content['preference_name']}*\"，为您推荐 {content['total_count']} 个项目：\n\n"

            for i, repo in enumerate(content['repositories'][:5], 1):  # 限制前5个
                message += f"{i}. *{repo['name']}*\n"
                message += f"   ⭐ {repo['stars']:,} stars | 💻 {repo['language'] or 'N/A'}\n"
                message += f"   📝 {repo['description'][:100]}{'...' if len(repo['description']) > 100 else ''}\n"
                message += f"   🎯 评分: {repo['score']:.2f}\n"
                message += f"   🔗 [查看项目]({repo['url']})\n\n"

            if len(content['repositories']) > 5:
                message += f"还有 {len(content['repositories']) - 5} 个项目，请在Web界面查看完整列表。\n\n"

            message += "🤖 GitHub Bot自动推荐"

            # 检查是否有系统配置的Telegram bot token
            from core.config import settings
            telegram_bot_token = getattr(settings, 'telegram_bot_token', None)

            if not telegram_bot_token:
                logger.error("No Telegram bot token configured in settings", chat_id=chat_id)
                return False

            # 使用真实的Telegram发送功能
            success = await send_telegram_message(telegram_bot_token, chat_id, message)
            logger.info("Telegram notification sent", chat_id=chat_id, success=success)
            return success

        except Exception as e:
            logger.error("Error preparing Telegram notification", error=str(e))
            return False

    async def _send_slack_notification(self, webhook_url: str, content: Dict[str, Any]) -> bool:
        """发送Slack通知"""
        try:
            blocks = [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": "🚀 GitHub项目推荐"
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"根据您的偏好 *{content['preference_name']}*，为您推荐 {content['total_count']} 个项目："
                    }
                }
            ]

            for repo in content['repositories'][:3]:  # 限制前3个
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*<{repo['url']}|{repo['name']}>*\n⭐ {repo['stars']:,} stars | 💻 {repo['language'] or 'N/A'}\n📝 {repo['description'][:150]}{'...' if len(repo['description']) > 150 else ''}\n🎯 评分: {repo['score']:.2f}"
                    }
                })

            message = {
                "blocks": blocks
            }

            # 使用真实的Slack发送功能
            success = await send_slack_message(webhook_url, message)
            logger.info("Slack notification sent", webhook_url=webhook_url[:50] + "...", success=success)
            return success

        except Exception as e:
            logger.error("Error preparing Slack notification", error=str(e))
            return False

    async def _send_wechat_notification(self, webhook_url: str, content: Dict[str, Any]) -> bool:
        """发送微信通知"""
        try:
            markdown_content = f"# 🚀 GitHub项目推荐\n\n"
            markdown_content += f"根据您的偏好 **{content['preference_name']}**，为您推荐 {content['total_count']} 个项目：\n\n"

            for i, repo in enumerate(content['repositories'][:5], 1):
                markdown_content += f"## {i}. [{repo['name']}]({repo['url']})\n"
                markdown_content += f"> ⭐ {repo['stars']:,} stars | 💻 {repo['language'] or 'N/A'}\n"
                markdown_content += f"> 📝 {repo['description'][:120]}{'...' if len(repo['description']) > 120 else ''}\n"
                markdown_content += f"> 🎯 评分: {repo['score']:.2f}\n\n"

            markdown_content += "\n🤖 GitHub Bot自动推荐"

            message = {
                "msgtype": "markdown",
                "markdown": {
                    "content": markdown_content
                }
            }

            # 使用真实的微信发送功能
            success = await send_wechat_message(webhook_url, message)
            logger.info("WeChat notification sent", webhook_url=webhook_url[:50] + "...", success=success)
            return success

        except Exception as e:
            logger.error("Error preparing WeChat notification", error=str(e))
            return False

    async def _update_recommendations_notification_status(
        self,
        recommendations: List[Recommendation],
        sent_channels: List[str]
    ):
        """更新推荐记录的通知状态"""
        try:
            for rec in recommendations:
                rec.sent_channels = sent_channels
                rec.sent_at = datetime.utcnow() if sent_channels else None

            self.db.commit()
            logger.info("Updated notification status", recommendations_count=len(recommendations), sent_channels=sent_channels)

        except Exception as e:
            logger.error("Error updating notification status", error=str(e))
            self.db.rollback()
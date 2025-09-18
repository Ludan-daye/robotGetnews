import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
import aiosmtplib
from core.config import settings
import structlog

logger = structlog.get_logger()


async def send_email(
    to_email: str,
    subject: str,
    content: str,
    smtp_host: Optional[str] = None,
    smtp_port: Optional[int] = None,
    smtp_username: Optional[str] = None,
    smtp_password: Optional[str] = None,
    use_tls: Optional[bool] = None
) -> bool:
    """
    Send email using aiosmtplib

    Args:
        to_email: 收件人邮箱
        subject: 邮件主题
        content: 邮件内容
        smtp_host: SMTP服务器地址（可选，默认使用配置）
        smtp_port: SMTP端口（可选，默认使用配置）
        smtp_username: SMTP用户名（可选，默认使用配置）
        smtp_password: SMTP密码（可选，默认使用配置）
        use_tls: 是否使用TLS（可选，默认使用配置）

    Returns:
        bool: 发送是否成功
    """
    try:
        # 使用传入的配置或默认配置
        host = smtp_host or getattr(settings, 'smtp_host', None)
        port = smtp_port or getattr(settings, 'smtp_port', 587)
        username = smtp_username or getattr(settings, 'smtp_username', None)
        password = smtp_password or getattr(settings, 'smtp_password', None)
        tls = use_tls if use_tls is not None else getattr(settings, 'smtp_tls', True)
        from_email = getattr(settings, 'email_from', None)

        # 如果使用传入参数，使用用户邮箱作为发件人
        if smtp_host and smtp_username:
            from_email = smtp_username

        if not all([host, username, password]):
            logger.error("SMTP configuration incomplete", host=host, username=username, has_password=bool(password))
            return False

        # 创建邮件
        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = from_email
        message["To"] = to_email

        # 添加HTML内容
        html_part = MIMEText(content, "html", "utf-8")
        message.attach(html_part)

        # 发送邮件
        await aiosmtplib.send(
            message,
            hostname=host,
            port=port,
            username=username,
            password=password,
            start_tls=tls,  # 使用STARTTLS而不是直接TLS
        )

        logger.info("Email sent successfully", to=to_email, subject=subject)
        return True

    except Exception as e:
        logger.error("Failed to send email", error=str(e), to=to_email, subject=subject)
        return False


async def send_test_email(
    to_email: str,
    smtp_host: str,
    smtp_port: int,
    smtp_username: str,
    smtp_password: str,
    use_tls: bool = True
) -> bool:
    """
    发送测试邮件

    Args:
        to_email: 收件人邮箱
        smtp_host: SMTP服务器地址
        smtp_port: SMTP端口
        smtp_username: SMTP用户名
        smtp_password: SMTP密码
        use_tls: 是否使用TLS

    Returns:
        bool: 发送是否成功
    """
    subject = "GitHub Bot 邮件通知测试"
    content = """
    <html>
      <body>
        <h2>GitHub Bot 邮件通知测试</h2>
        <p>恭喜！您的邮件通知配置已成功设置。</p>
        <p>GitHub Bot 现在可以向这个邮箱发送项目推荐通知了。</p>
        <hr>
        <p><small>这是一封测试邮件，由 GitHub Bot WebUI 发送。</small></p>
      </body>
    </html>
    """

    return await send_email(
        to_email=to_email,
        subject=subject,
        content=content,
        smtp_host=smtp_host,
        smtp_port=smtp_port,
        smtp_username=smtp_username,
        smtp_password=smtp_password,
        use_tls=use_tls
    )


async def send_recommendation_email(
    to_email: str,
    recommendations: list,
    user_name: str = "用户"
) -> bool:
    """
    发送项目推荐邮件

    Args:
        to_email: 收件人邮箱
        recommendations: 推荐列表
        user_name: 用户名

    Returns:
        bool: 发送是否成功
    """
    if not recommendations:
        return False

    subject = f"GitHub Bot - 为您推荐了 {len(recommendations)} 个项目"

    # 构建邮件内容
    content = f"""
    <html>
      <body>
        <h2>GitHub 项目推荐</h2>
        <p>亲爱的 {user_name}，</p>
        <p>我们为您找到了以下优质项目：</p>
        <div style="margin: 20px 0;">
    """

    for i, rec in enumerate(recommendations, 1):
        repo = rec.get('repo', {})
        content += f"""
          <div style="border: 1px solid #ddd; padding: 15px; margin: 10px 0; border-radius: 5px;">
            <h3 style="margin: 0 0 10px 0;">
              <a href="{repo.get('html_url', '#')}" style="color: #0366d6; text-decoration: none;">
                {i}. {repo.get('full_name', 'Unknown Repository')}
              </a>
            </h3>
            <p style="margin: 5px 0; color: #666;">
              ⭐ {repo.get('stargazers_count', 0)} stars |
              🍴 {repo.get('forks_count', 0)} forks |
              📝 {repo.get('language', 'Unknown')}
            </p>
            <p style="margin: 10px 0;">{repo.get('description', '暂无描述')}</p>
            <p style="margin: 5px 0; font-size: 12px; color: #888;">
              推荐分数: {rec.get('score', 0):.1f} |
              推荐理由: {rec.get('reason_summary', '匹配您的偏好')}
            </p>
          </div>
        """

    content += """
        </div>
        <p>希望这些项目对您有帮助！</p>
        <hr>
        <p><small>
          这封邮件由 GitHub Bot WebUI 自动发送。<br>
          如果您不希望再收到这些邮件，请登录系统修改通知设置。
        </small></p>
      </body>
    </html>
    """

    return await send_email(
        to_email=to_email,
        subject=subject,
        content=content
    )
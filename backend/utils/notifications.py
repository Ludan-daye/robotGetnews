import httpx
import structlog
from typing import Optional

logger = structlog.get_logger()


async def send_telegram_message(
    bot_token: str,
    chat_id: str,
    message: str
) -> bool:
    """
    发送Telegram消息

    Args:
        bot_token: Telegram Bot Token
        chat_id: 聊天ID
        message: 消息内容

    Returns:
        bool: 发送是否成功
    """
    try:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        data = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "Markdown"
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=data)

        if response.status_code == 200:
            logger.info("Telegram message sent successfully", chat_id=chat_id)
            return True
        else:
            logger.error("Failed to send Telegram message", status_code=response.status_code, response=response.text)
            return False

    except Exception as e:
        logger.error("Exception sending Telegram message", error=str(e))
        return False


async def send_slack_message(
    webhook_url: str,
    message: dict
) -> bool:
    """
    发送Slack消息

    Args:
        webhook_url: Slack Webhook URL
        message: 消息内容

    Returns:
        bool: 发送是否成功
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(webhook_url, json=message)

        if response.status_code == 200:
            logger.info("Slack message sent successfully")
            return True
        else:
            logger.error("Failed to send Slack message", status_code=response.status_code, response=response.text)
            return False

    except Exception as e:
        logger.error("Exception sending Slack message", error=str(e))
        return False


async def send_wechat_message(
    webhook_url: str,
    message: dict
) -> bool:
    """
    发送企业微信消息

    Args:
        webhook_url: 企业微信Webhook URL
        message: 消息内容

    Returns:
        bool: 发送是否成功
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(webhook_url, json=message)

        if response.status_code == 200:
            result = response.json()
            if result.get("errcode") == 0:
                logger.info("WeChat message sent successfully")
                return True
            else:
                logger.error("WeChat API returned error", errcode=result.get("errcode"), errmsg=result.get("errmsg"))
                return False
        else:
            logger.error("Failed to send WeChat message", status_code=response.status_code, response=response.text)
            return False

    except Exception as e:
        logger.error("Exception sending WeChat message", error=str(e))
        return False


async def send_test_telegram(bot_token: str, chat_id: str) -> bool:
    """发送Telegram测试消息"""
    message = """🤖 *GitHub Bot WebUI 测试消息*

这是一条测试消息，如果您收到此消息，说明Telegram通知配置成功！

✅ 配置正确
📱 通知渠道已激活"""

    return await send_telegram_message(bot_token, chat_id, message)


async def send_test_slack(webhook_url: str) -> bool:
    """发送Slack测试消息"""
    message = {
        "text": "🤖 GitHub Bot WebUI 测试消息",
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*GitHub Bot WebUI 测试消息* 🎉\n\n这是一条测试消息，如果您收到此消息，说明Slack通知配置成功！\n\n✅ 配置正确\n📱 通知渠道已激活"
                }
            }
        ]
    }

    return await send_slack_message(webhook_url, message)


async def send_test_wechat(webhook_url: str) -> bool:
    """发送企业微信测试消息"""
    import time

    message = {
        "msgtype": "markdown",
        "markdown": {
            "content": f"""# GitHub Bot WebUI 测试消息 🤖

这是一条测试消息，如果您收到此消息，说明企业微信通知配置成功！

> ✅ 配置正确
> 📱 通知渠道已激活
> 🕐 测试时间：{time.strftime('%Y-%m-%d %H:%M:%S')}"""
        }
    }

    return await send_wechat_message(webhook_url, message)
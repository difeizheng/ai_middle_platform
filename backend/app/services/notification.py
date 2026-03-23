"""
告警通知服务

支持多种通知渠道:
- Email (SMTP)
- 钉钉 (DingTalk)
- 企业微信 (WeCom)
- Webhook
"""
import json
import smtplib
import asyncio
from typing import Dict, Any, List, Optional
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.core.logger import get_logger
from app.core.config import settings

logger = get_logger(__name__)


class NotificationChannel:
    """通知渠道基类"""

    async def send(self, title: str, content: str, **kwargs) -> bool:
        """发送通知"""
        raise NotImplementedError


class EmailNotification(NotificationChannel):
    """邮件通知"""

    def __init__(self, config: Dict[str, Any]):
        self.smtp_server = config.get("smtp_server", "")
        self.smtp_port = config.get("smtp_port", 587)
        self.username = config.get("username", "")
        self.password = config.get("password", "")
        self.from_addr = config.get("from_addr", self.username)
        self.to_addrs = config.get("to_addrs", [])
        self.use_tls = config.get("use_tls", True)

    async def send(self, title: str, content: str, **kwargs) -> bool:
        """发送邮件通知"""
        try:
            msg = MIMEMultipart()
            msg["From"] = self.from_addr
            msg["To"] = ", ".join(self.to_addrs)
            msg["Subject"] = title

            # 添加 HTML 内容
            html_content = kwargs.get("html", f"<pre>{content}</pre>")
            msg.attach(MIMEText(html_content, "html", "utf-8"))

            # 异步发送邮件
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                self._send_email_sync,
                msg.as_string(),
            )

            logger.info(f"邮件通知已发送：{title}")
            return True

        except Exception as e:
            logger.error(f"邮件通知发送失败：{e}")
            return False

    def _send_email_sync(self, message: str):
        """同步发送邮件"""
        server = smtplib.SMTP(self.smtp_server, self.smtp_port)
        if self.use_tls:
            server.starttls()
        if self.username and self.password:
            server.login(self.username, self.password)
        server.sendmail(self.from_addr, self.to_addrs, message)
        server.quit()


class DingTalkNotification(NotificationChannel):
    """钉钉机器人通知"""

    def __init__(self, config: Dict[str, Any]):
        self.webhook_url = config.get("webhook_url", "")
        self.secret = config.get("secret", "")

    async def send(self, title: str, content: str, **kwargs) -> bool:
        """发送钉钉通知"""
        try:
            import httpx

            # 构建消息
            message = {
                "msgtype": "markdown",
                "markdown": {
                    "title": title,
                    "text": f"## {title}\n\n{content}",
                },
                "at": {
                    "isAtAll": kwargs.get("at_all", True),
                },
            }

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    self.webhook_url,
                    json=message,
                    headers={"Content-Type": "application/json"},
                )
                result = response.json()

                if result.get("errcode") == 0:
                    logger.info(f"钉钉通知已发送：{title}")
                    return True
                else:
                    logger.error(f"钉钉通知发送失败：{result}")
                    return False

        except Exception as e:
            logger.error(f"钉钉通知发送失败：{e}")
            return False


class WeComNotification(NotificationChannel):
    """企业微信机器人通知"""

    def __init__(self, config: Dict[str, Any]):
        self.webhook_url = config.get("webhook_url", "")

    async def send(self, title: str, content: str, **kwargs) -> bool:
        """发送企业微信通知"""
        try:
            import httpx

            # 构建消息
            message = {
                "msgtype": "markdown",
                "markdown": {
                    "content": f"## {title}\n{content}",
                },
            }

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    self.webhook_url,
                    json=message,
                    headers={"Content-Type": "application/json"},
                )
                result = response.json()

                if result.get("errcode") == 0:
                    logger.info(f"企业微信通知已发送：{title}")
                    return True
                else:
                    logger.error(f"企业微信通知发送失败：{result}")
                    return False

        except Exception as e:
            logger.error(f"企业微信通知发送失败：{e}")
            return False


class WebhookNotification(NotificationChannel):
    """通用 Webhook 通知"""

    def __init__(self, config: Dict[str, Any]):
        self.webhook_url = config.get("url", "")
        self.method = config.get("method", "POST")
        self.headers = config.get("headers", {"Content-Type": "application/json"})
        self.template = config.get("template", None)

    async def send(self, title: str, content: str, **kwargs) -> bool:
        """发送 Webhook 通知"""
        try:
            import httpx

            # 构建 payload
            if self.template:
                # 使用模板
                payload = self._render_template(self.template, title, content, kwargs)
            else:
                # 默认格式
                payload = {
                    "title": title,
                    "content": content,
                    "timestamp": asyncio.get_event_loop().time(),
                    **kwargs,
                }

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.request(
                    self.method,
                    self.webhook_url,
                    json=payload,
                    headers=self.headers,
                )
                response.raise_for_status()

                logger.info(f"Webhook 通知已发送：{title}")
                return True

        except Exception as e:
            logger.error(f"Webhook 通知发送失败：{e}")
            return False

    def _render_template(self, template: str, title: str, content: str, kwargs: dict) -> dict:
        """渲染模板"""
        # 简单的字符串替换
        result = template
        result = result.replace("{{title}}", title)
        result = result.replace("{{content}}", content)
        for key, value in kwargs.items():
            result = result.replace(f"{{{key}}}", str(value))
        return json.loads(result)


class AlertNotifier:
    """
    告警通知器

    支持配置多个通知渠道，可以同时发送到多个目标
    """

    def __init__(self):
        self._channels: Dict[str, NotificationChannel] = {}

    def add_channel(self, name: str, channel: NotificationChannel):
        """添加通知渠道"""
        self._channels[name] = channel
        logger.info(f"通知渠道已添加：{name}")

    def remove_channel(self, name: str):
        """移除通知渠道"""
        if name in self._channels:
            del self._channels[name]

    async def notify(
        self,
        title: str,
        content: str,
        channels: Optional[List[str]] = None,
        **kwargs,
    ) -> Dict[str, bool]:
        """
        发送通知到指定渠道

        Args:
            title: 通知标题
            content: 通知内容
            channels: 指定渠道列表，None 表示发送到所有渠道
            **kwargs: 额外参数

        Returns:
            发送结果字典
        """
        results = {}

        target_channels = channels or list(self._channels.keys())

        for channel_name in target_channels:
            channel = self._channels.get(channel_name)
            if channel:
                try:
                    success = await channel.send(title, content, **kwargs)
                    results[channel_name] = success
                except Exception as e:
                    logger.error(f"通知渠道 {channel_name} 发送失败：{e}")
                    results[channel_name] = False
            else:
                logger.warning(f"通知渠道不存在：{channel_name}")
                results[channel_name] = False

        return results

    async def notify_alert(self, alert_data: Dict[str, Any]) -> Dict[str, bool]:
        """
        发送告警通知

        Args:
            alert_data: 告警数据，包含 rule_name, metric_value, threshold 等

        Returns:
            发送结果字典
        """
        title = f"🚨 告警：{alert_data.get('rule_name', '未知告警')}"
        content = self._format_alert_content(alert_data)

        return await self.notify(title, content, **alert_data.get("notify_kwargs", {}))

    def _format_alert_content(self, alert_data: Dict[str, Any]) -> str:
        """格式化告警内容"""
        lines = [
            f"**告警规则**: {alert_data.get('rule_name', 'N/A')}",
            f"**指标名称**: {alert_data.get('metric_name', 'N/A')}",
            f"**当前值**: {alert_data.get('metric_value', 'N/A')}",
            f"**阈值**: {alert_data.get('threshold', 'N/A')}",
            f"**严重程度**: {alert_data.get('severity', 'N/A')}",
            f"**触发时间**: {alert_data.get('fired_at', 'N/A')}",
        ]

        if alert_data.get("message"):
            lines.append(f"\n**详情**: {alert_data['message']}")

        return "\n".join(lines)


# 全局通知器实例
_global_notifier: Optional[AlertNotifier] = None


def get_notifier() -> AlertNotifier:
    """获取全局通知器"""
    global _global_notifier
    if _global_notifier is None:
        _global_notifier = AlertNotifier()
    return _global_notifier


def setup_notification_channels():
    """
    从配置加载通知渠道

    在应用启动时调用
    """
    notifier = get_notifier()

    # 从配置加载渠道
    notification_config = settings.NOTIFICATION_CHANNELS or {}

    for name, config in notification_config.items():
        channel_type = config.get("type", "")
        channel_config = config.get("config", {})

        channel: Optional[NotificationChannel] = None

        if channel_type == "email":
            channel = EmailNotification(channel_config)
        elif channel_type == "dingtalk":
            channel = DingTalkNotification(channel_config)
        elif channel_type == "wecom":
            channel = WeComNotification(channel_config)
        elif channel_type == "webhook":
            channel = WebhookNotification(channel_config)
        else:
            logger.warning(f"未知通知渠道类型：{channel_type}")
            continue

        if channel:
            notifier.add_channel(name, channel)

    logger.info(f"通知渠道加载完成，共 {len(notifier._channels)} 个渠道")


async def send_alert(alert_data: Dict[str, Any]) -> Dict[str, bool]:
    """
    发送告警通知的便捷函数

    Args:
        alert_data: 告警数据

    Returns:
        发送结果字典
    """
    notifier = get_notifier()
    return await notifier.notify_alert(alert_data)

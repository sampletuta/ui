"""
Notification utility that integrates with django-notifications-hq
"""

import logging
from django.contrib.contenttypes.models import ContentType

logger = logging.getLogger(__name__)

def notify(recipient, actor, verb, target=None, description=None, action_object=None, **kwargs):
    """
    Create notifications using django-notifications-hq
    """
    try:
        from notifications.signals import notify as django_notify
        
        # Create the notification using django-notifications-hq
        django_notify.send(
            sender=actor,
            recipient=recipient,
            verb=verb,
            target=target,
            action_object=action_object,
            description=description,
            **kwargs
        )
        
        # Log the notification for debugging
        message = f"Notification: {actor} {verb}"
        if target:
            message += f" {target}"
        if description:
            message += f" - {description}"
        logger.info(f"NOTIFICATION for {recipient}: {message}")

    except ImportError:
        # Fallback to simple logging if django-notifications-hq is not available
        logger.warning("django-notifications-hq not available, falling back to logging")
        message = f"Notification: {actor} {verb}"
        if target:
            message += f" {target}"
        if description:
            message += f" - {description}"
        logger.info(f"NOTIFICATION for {recipient}: {message}")
        
    except Exception as e:
        logger.error(f"Error sending notification: {e}")

def send_notification_email(recipient, message):
    """
    Placeholder for email notification functionality
    Implement this if you want to send actual emails
    """
    pass

# Notification class that mimics django-notifications-hq API
class Notification:
    """
    Notification class that provides send method for compatibility
    """
    @staticmethod
    def send(sender, recipient, verb, target=None, action_object=None, description=None, **kwargs):
        """
        Send a notification using the notify function
        """
        return notify(
            recipient=recipient,
            actor=sender,
            verb=verb,
            target=target,
            action_object=action_object,
            description=description,
            **kwargs
        )

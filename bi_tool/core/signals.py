from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.signals import user_logged_in, user_logged_out
import logging

from .models import User, UserSession

logger = logging.getLogger(__name__)


@receiver(post_save, sender=User)
def user_post_save(sender, instance, created, **kwargs):
    """
    Signal handler for User model post-save events
    """
    if created:
        logger.info(f"New user created: {instance.username} with role {instance.role}")
        
        # You can add additional logic here, such as:
        # - Sending welcome email
        # - Creating default user preferences
        # - Assigning default permissions
        # - Notifying admins of new user registration


@receiver(user_logged_in)
def user_logged_in_handler(sender, request, user, **kwargs):
    """
    Signal handler for user login events
    """
    logger.info(f"User logged in: {user.username}")
    
    # Update last login time is handled by Django automatically
    # You can add additional login logic here


@receiver(user_logged_out)
def user_logged_out_handler(sender, request, user, **kwargs):
    """
    Signal handler for user logout events  
    """
    if user:
        logger.info(f"User logged out: {user.username}")
        
        # Deactivate user sessions
        UserSession.objects.filter(
            user=user,
            is_active=True
        ).update(is_active=False)
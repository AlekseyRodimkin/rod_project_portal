from django.db.models.signals import post_delete
from django.dispatch import receiver

from .models import Profile


@receiver(post_delete, sender=Profile)
def delete_avatar_file(sender, instance, **kwargs):
    """Сигнал на удаление аватара при удалении профиля"""
    if instance.avatar:
        instance.avatar.delete(save=False)
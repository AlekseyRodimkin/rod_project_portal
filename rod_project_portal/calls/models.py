from django.conf import settings
from django.db import models
import uuid


class Friendship(models.Model):
    """Модель для управления списком друзей и заявками в друзья"""

    class Status(models.TextChoices):
        PENDING = "pending", "В ожидании"
        ACCEPTED = "accepted", "Друзья"
        BLOCKED = "blocked", "Заблокирован"

    from_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="friendship_requests_sent",
        verbose_name="Инициатор",
    )
    to_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="friendship_requests_received",
        verbose_name="Получатель",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name="Статус",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")
    room_name = models.CharField(
        max_length=100, unique=True, blank=True, verbose_name="Комната для звонка"
    )

    def save(self, *args, **kwargs):
        if not self.room_name:
            # Генерируем уникальное имя комнаты при создании связи
            self.room_name = f"room_{uuid.uuid4().hex[:16]}"
        super().save(*args, **kwargs)

    class Meta:
        unique_together = ("from_user", "to_user")
        verbose_name = "Дружба / Заявка"
        verbose_name_plural = "Список друзей и заявок"

    def __str__(self):
        return f"{self.from_user} -> {self.to_user} ({self.get_status_display()})"


class CallHistory(models.Model):
    """Модель для хранения истории видеозвонков"""

    class CallStatus(models.TextChoices):
        COMPLETED = "completed", "Завершен"
        MISSED = "missed", "Пропущен"
        CANCELLED = "cancelled", "Отменен"

    caller = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="calls_initiated",
        verbose_name="Кто звонил",
    )
    callee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="calls_received",
        verbose_name="Кому звонили",
    )
    room_name = models.CharField(
        max_length=100, blank=True, verbose_name="Название комнаты"
    )
    start_time = models.DateTimeField(auto_now_add=True, verbose_name="Время начала")
    end_time = models.DateTimeField(
        null=True, blank=True, verbose_name="Время окончания"
    )
    status = models.CharField(
        max_length=20,
        choices=CallStatus.choices,
        default=CallStatus.COMPLETED,
        verbose_name="Статус звонка",
    )

    class Meta:
        verbose_name = "История звонка"
        verbose_name_plural = "История звонков"
        ordering = ["-start_time"]

    def __str__(self):
        caller_name = self.caller.username if self.caller else "Неизвестно"
        callee_name = self.callee.username if self.callee else "Неизвестно"
        return f"Звонок: {caller_name} ➔ {callee_name} ({self.get_status_display()})"


class PushSubscription(models.Model):
    """Модель подписок для уведомлений"""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="push_subscriptions",
        verbose_name="Пользователь",
    )
    endpoint = models.TextField(unique=True, verbose_name="Адрес подписки")
    p256dh = models.CharField(max_length=255, verbose_name="Ключ p256dh")
    auth = models.CharField(max_length=255, verbose_name="Ключ auth")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создана")

    class Meta:
        verbose_name = "Push-подписка"
        verbose_name_plural = "Push-подписки"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} — {self.endpoint[:40]}…"

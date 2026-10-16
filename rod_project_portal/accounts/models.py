from django.contrib.auth.models import User
from django.db import models


class Item(models.Model):
    """Модель товара"""
    name = models.CharField(max_length=100, null=False, blank=False)
    location = models.CharField(max_length=100, default=None, null=False, blank=False)
    ip = models.CharField(max_length=30, null=True, blank=True)
    description = models.TextField(blank=True, max_length=500, null=True)
    instructions = models.TextField(blank=True, max_length=500, null=True)
    available = models.BooleanField(default=False, null=False, blank=False)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def instructions_short(self) -> str:
        return (
            self.instructions
            if not self.instructions or len(self.instructions) < 48
            else self.instructions[:48] + "..."
        )

    @property
    def description_short(self) -> str:
        return (
            self.description
            if len(self.description) < 48
            else self.description[:48] + "..."
        )


class VPN(Item):
    """Модель VPN"""

    class Meta:
        ordering = ["name"]
        verbose_name = "VPN"
        verbose_name_plural = "VPN"

    def __str__(self):
        return f"{self.name}"


class Proxy(Item):
    """Модель Proxy"""
    port = models.CharField(null=True, blank=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Proxy"
        verbose_name_plural = "Proxy"

    def __str__(self):
        return f"{self.name}"


class UserProxy(models.Model):
    """Сводная таблица пользователей и прокси"""
    proxy = models.ForeignKey(
        Proxy, on_delete=models.CASCADE, related_name="proxy_users",
    )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="user_proxies",
    )
    username = models.CharField(max_length=150, blank=True, null=True, unique=False)
    key = models.TextField(max_length=500, null=True, blank=True)
    secret = models.TextField(max_length=500, null=True, blank=True)
    url = models.CharField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def key_short(self) -> str:
        return (
            self.key
            if not self.key or len(self.key) < 28
            else self.key[:28] + "..."
        )

    @property
    def url_short(self) -> str:
        return (
            self.url
            if not self.url or len(self.url) < 28
            else self.url[:28] + "..."
        )

    @property
    def secret_short(self) -> str:
        return (
            self.secret
            if not self.secret or len(self.secret) < 28
            else self.secret[:28] + "..."
        )

    class Meta:
        ordering = ["user"]
        verbose_name = "UserProxy"
        verbose_name_plural = "UserProxy"


class UserVPN(models.Model):
    """Сводная таблица пользователей и VPN"""
    vpn = models.ForeignKey(
        VPN, on_delete=models.CASCADE, related_name="vpn_users",
    )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="user_vpns"
    )
    username = models.CharField(max_length=150, blank=True, null=True, unique=False)
    key = models.TextField(max_length=500, null=True, blank=True)
    secret = models.TextField(max_length=500, null=True, blank=True)
    url = models.CharField(null=True, blank=True)
    qr_url = models.URLField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def key_short(self) -> str:
        return (
            self.key
            if not self.key or len(self.key) < 28
            else self.key[:28] + "..."
        )

    @property
    def url_short(self) -> str:
        return (
            self.url
            if not self.url or len(self.url) < 28
            else self.url[:28] + "..."
        )

    @property
    def secret_short(self) -> str:
        return (
            self.secret
            if not self.secret or len(self.secret) < 28
            else self.secret[:28] + "..."
        )

    class Meta:
        ordering = ["user"]
        verbose_name = "UserVPN"
        verbose_name_plural = "UserVPN"


class UserTickets(models.Model):
    """Таблица обращений"""
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="user_tickets"
    )
    vpn = models.ForeignKey(
        VPN, on_delete=models.CASCADE, related_name="user_vpn_tickets", null=True, blank=True
    )
    proxy = models.ForeignKey(
        Proxy, on_delete=models.CASCADE, related_name="user_proxy_tickets", null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Обращение"
        verbose_name_plural = "Обращения"


class GlobalNotification(models.Model):
    """Общее уведомление для всех пользователей"""

    class Type(models.TextChoices):
        INFO = 'info', 'Информация'
        SUCCESS = 'success', 'Успех'
        WARNING = 'warning', 'Предупреждение'
        DANGER = 'danger', 'Ошибка'

    title = models.CharField(max_length=200)
    message = models.TextField()
    type = models.CharField(max_length=20, choices=Type.choices, default=Type.INFO)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Общее уведомление"
        verbose_name_plural = "Общие уведомления"
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class UserNotification(models.Model):
    """Персональное уведомление"""

    class Type(models.TextChoices):
        INFO = 'info', 'Информация'
        SUCCESS = 'success', 'Успех'
        WARNING = 'warning', 'Предупреждение'
        DANGER = 'danger', 'Ошибка'

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications")
    title = models.CharField(max_length=200)
    message = models.TextField()
    type = models.CharField(max_length=20, choices=Type.choices, default=Type.INFO)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    @classmethod
    def create_with_limit(cls, user, title, message, type, limit=10):
        """Создаёт уведомление и удаляет старые, оставляя только последние limit штук"""
        notification = cls.objects.create(
            user=user,
            title=title,
            message=message,
            type=type
        )

        old_notifications_ids = cls.objects.filter(user=user).order_by('-created_at').values_list('id', flat=True)[
            limit:]
        if old_notifications_ids:
            cls.objects.filter(id__in=old_notifications_ids).delete()

        return notification

    class Meta:
        verbose_name = "Персональное уведомление"
        verbose_name_plural = "Персональные уведомления"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username}: {self.title}"

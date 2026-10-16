from django import forms
from django.contrib import admin

from .models import (
    Proxy,
    VPN,
    UserProxy,
    UserVPN,
    UserTickets,
    GlobalNotification,
    UserNotification,
)

"""
Опции административной панели

list_display - отображаемые поля
list_display_links - поля-ссылки для перехода к объекту
ordering - начальная сортировка при отображении в адм. панели
search_fields - поля используемые при поиске из адм. панели
list_filter - сортировки
readonly_fields - блокировка изменяемости
search_help_text - описание поля поиска
list_per_page - кол-во строк в таблице
list_editable - изменяемые колонки


Опции связанных объектов

select_related - для связи <One to One>
class ...Inline - для связи <One to Many> и <Many to Many>
"""


@admin.register(VPN)
class VPNAdmin(admin.ModelAdmin):
    list_display = (
        "pk",
        "name",
        "available",
        "location",
        "ip",
        "description_short",
        "instructions_short",
        "created_at",
    )
    list_display_links = (
        "pk",
        "name",
    )
    ordering = (
        "pk",
        "name",
    )
    list_filter = [
        "created_at",
        "location",
        "ip",
    ]
    readonly_fields = ["created_at"]
    search_fields = (
        "name",
        "location",
        "ip",
        "description",
        "instructions",
    )
    list_per_page = 25


@admin.register(Proxy)
class ProxyAdmin(admin.ModelAdmin):
    list_display = (
        "pk",
        "name",
        "available",
        "location",
        "ip",
        "port",
        "description_short",
        "instructions_short",
        "created_at",
    )
    list_display_links = (
        "pk",
        "name",
    )
    ordering = (
        "pk",
        "name",
    )
    list_filter = [
        "created_at",
        "location",
        "ip",
    ]
    readonly_fields = ["created_at"]
    search_fields = (
        "name",
        "location",
        "ip",
        "description",
        "instructions",
    )
    list_per_page = 25


@admin.register(UserProxy)
class UserProxyAdmin(admin.ModelAdmin):
    list_display = (
        "pk",
        "proxy",
        "user",
        "key_short",
        "username",
        "url_short",
        "secret_short",
        "created_at",
    )
    list_display_links = (
        "pk",
        "proxy",
    )
    ordering = ("pk",)
    list_filter = ["created_at", "user"]
    readonly_fields = ["created_at"]
    list_per_page = 25


@admin.register(UserVPN)
class UserVPNAdmin(admin.ModelAdmin):
    list_display = (
        "pk",
        "vpn",
        "user",
        "key_short",
        "username",
        "url_short",
        "secret_short",
        "qr_url",
        "created_at",
    )
    list_display_links = (
        "pk",
        "vpn",
    )
    ordering = ("pk",)
    list_filter = ["created_at", "user"]
    readonly_fields = ["created_at"]
    list_per_page = 25


@admin.register(UserTickets)
class UserTicketsAdmin(admin.ModelAdmin):
    list_display = (
        "pk",
        "user",
        "vpn",
        "proxy",
        "created_at",
    )
    list_display_links = (
        "pk",
        "user",
    )
    ordering = ("created_at",)
    list_filter = ["created_at", "user"]
    readonly_fields = ["created_at"]
    list_per_page = 25


@admin.register(GlobalNotification)
class GlobalNotificationAdmin(admin.ModelAdmin):
    list_display = ("pk", "title", "type", "is_active", "created_at")
    list_display_links = (
        "pk",
        "title",
    )
    list_filter = ["type", "is_active", "created_at"]
    search_fields = ["title", "message"]
    readonly_fields = ["created_at"]
    list_per_page = 25


@admin.register(UserNotification)
class UserNotificationAdmin(admin.ModelAdmin):
    list_display = ("pk", "user", "title", "type", "is_read", "created_at")
    list_display_links = (
        "pk",
        "user",
        "title",
    )
    list_filter = ["type", "is_read", "created_at", "user"]
    search_fields = ["user__username", "title", "message"]
    readonly_fields = ["created_at"]
    list_per_page = 25

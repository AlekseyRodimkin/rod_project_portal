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

from django.contrib import admin
from .models import Friendship, CallHistory, PushSubscription


@admin.register(Friendship)
class FriendshipAdmin(admin.ModelAdmin):
    list_display = ("from_user", "to_user", "status", "created_at")
    list_display_links = ("cfrom_useraller", "to_user")
    list_filter = ("status", "created_at")
    search_fields = ("from_user__username", "to_user__username")
    list_per_page = 25


@admin.register(CallHistory)
class CallHistoryAdmin(admin.ModelAdmin):
    list_display = ("caller", "callee", "room_name", "status", "start_time", "end_time")
    list_display_links = ("caller", "callee")
    list_filter = ("status", "start_time")
    search_fields = ("caller__username", "callee__username", "room_name")
    list_per_page = 25


@admin.register(PushSubscription)
class PushSubscriptionAdmin(admin.ModelAdmin):
    list_display = ("user", "short_endpoint", "created_at")
    list_filter = ("created_at",)
    search_fields = ("user__username", "endpoint")
    readonly_fields = ("endpoint", "p256dh", "auth", "created_at")

    @admin.display(description="Адрес подписки")
    def short_endpoint(self, obj):
        return obj.endpoint[:60] + "…"

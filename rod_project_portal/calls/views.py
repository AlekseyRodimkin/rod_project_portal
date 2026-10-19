from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from accounts.models import UserNotification
from django.db.models import Q
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404, redirect
from .models import Friendship, CallHistory, PushSubscription
from django.contrib import messages
import json
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, FileResponse
from django.views.decorators.http import require_POST
from django.conf import settings

User = get_user_model()


class CallView(LoginRequiredMixin, TemplateView):
    template_name = "calls/call.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        room_name = kwargs.get("room_name", "test")
        context["room_name"] = room_name

        callee = None
        # Ищем дружбу, к которой привязана эта комната
        friendship = Friendship.objects.filter(room_name=room_name).first()

        if friendship:
            # Если текущий пользователь - это инициатор, то цель звонка - получатель. И наоборот
            if friendship.from_user == user:
                callee = friendship.to_user
            else:
                callee = friendship.from_user

        # Создаем запись в истории звонков
        CallHistory.objects.create(
            caller=user,
            callee=callee,
            room_name=room_name,
            status=CallHistory.CallStatus.COMPLETED,
        )

        return context


class ContactsView(LoginRequiredMixin, TemplateView):
    template_name = "calls/contacts.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context["vapid_public_key"] = settings.VAPID_PUBLIC_KEY

        # Поиск пользователей
        search_query = self.request.GET.get("q", "").strip()
        search_results = []
        if (
            search_query and len(search_query) >= 2
        ):  # Ищем пользователей, исключая самого себя
            search_results = User.objects.filter(
                username__icontains=search_query
            ).exclude(id=user.id)[:5]

        # Получаем список друзей (где текущий пользователь либо from_user, либо to_user со статусом 'accepted')
        friendships = Friendship.objects.filter(
            (Q(from_user=user) | Q(to_user=user)) & Q(status=Friendship.Status.ACCEPTED)
        ).select_related("from_user", "to_user")

        friends = []
        for f in friendships:
            friend = f.to_user if f.from_user == user else f.from_user
            friends.append({"user": friend, "room_name": f.room_name})

        # История звонков для текущего пользователя
        call_history = CallHistory.objects.filter(
            Q(caller=user) | Q(callee=user)
        ).select_related("caller", "callee")[:5]

        context["search_query"] = search_query
        context["search_results"] = search_results
        context["friends"] = friends
        context["call_history"] = call_history
        return context

    def post(self, request, *args, **kwargs):
        """Обработка добавления в друзья"""
        user = request.user
        action = request.POST.get("action")
        target_user_id = request.POST.get("user_id")
        target_user = User.objects.get(id=target_user_id)

        # Добавляем в друзья
        if action == "add_friend" and target_user_id:
            target_user = get_object_or_404(User, id=target_user_id)
            if target_user != user:
                # Проверяем, существует ли уже связь
                friendship, created = Friendship.objects.get_or_create(
                    from_user=user,
                    to_user=target_user,
                    defaults={
                        "status": Friendship.Status.ACCEPTED
                    },  # Сразу добавляем в друзья
                )
                if not created and friendship.status != Friendship.Status.ACCEPTED:
                    friendship.status = Friendship.Status.ACCEPTED
                    friendship.save()

        # Создаем уведомление другу
        UserNotification.create_with_limit(
            user=target_user,
            title=f"Вас добавили в друзья",
            message=f"Пользователь {user.username} добавил вас в друзья",
            type=UserNotification.Type.INFO,
        )

        # Создаем Всплывающее уведомление об успешном добавлении
        messages.success(request, f"{target_user.get_username()} добавлен(а) в друзья")
        return redirect("calls:contacts")


@login_required
@require_POST
def push_subscribe(request):
    """Для браузерных уведомлений"""
    data = json.loads(request.body)
    PushSubscription.objects.update_or_create(
        endpoint=data['endpoint'],
        defaults={'user': request.user,
                  'p256dh': data['keys']['p256dh'],
                  'auth': data['keys']['auth']},
    )
    return JsonResponse({'ok': True})

from django.urls import reverse_lazy
from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth.views import LogoutView, LoginView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.views.generic import TemplateView, ListView
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit

from .models import (
    UserProxy,
    UserVPN,
    VPN,
    Proxy,
    UserTickets,
    UserNotification,
    GlobalNotification,
)


@method_decorator(
    ratelimit(key="ip", rate="5/10m", method="POST", block=True), name="dispatch"
)
class AppLoginView(LoginView):
    template_name = "accounts/login.html"
    redirect_authenticated_user = True
    next_page = "accounts:main"


class AppLogoutView(LoginRequiredMixin, LogoutView):
    next_page = reverse_lazy("accounts:login")


class Main(LoginRequiredMixin, TemplateView):
    template_name = "accounts/main.html"


class ServicesView(LoginRequiredMixin, TemplateView):
    template_name = "accounts/services.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Получаем текущие VPN и Proxy пользователя
        user_vpns = UserVPN.objects.filter(user=user).select_related("vpn")
        user_proxies = UserProxy.objects.filter(user=user).select_related("proxy")

        # Получаем ID тех, что уже есть у пользователя
        user_vpn_ids = user_vpns.values_list("vpn_id", flat=True)
        user_proxy_ids = user_proxies.values_list("proxy_id", flat=True)

        # Все доступные VPN и Proxy
        all_vpns = VPN.objects.all().order_by("created_at")
        all_proxies = Proxy.objects.all().order_by("created_at")

        # Те, которых нет у пользователя
        available_vpns = all_vpns.exclude(id__in=user_vpn_ids)
        available_proxies = all_proxies.exclude(id__in=user_proxy_ids)

        context["user_vpns"] = user_vpns
        context["user_proxies"] = user_proxies
        context["available_vpns"] = available_vpns
        context["available_proxies"] = available_proxies

        return context


@login_required
def create_ticket(request):
    if request.method == "POST":
        service_type = request.POST.get("service_type")
        service_id = request.POST.get("service_id")
        ticket = UserTickets(user=request.user)

        if service_type == "vpn":
            ticket.vpn = VPN.objects.get(id=service_id)
            notif = VPN.objects.get(id=service_id).name
        elif service_type == "proxy":
            ticket.proxy = Proxy.objects.get(id=service_id)
            notif = Proxy.objects.get(id=service_id).name

        ticket.save()

        # Создаём персональное уведомление
        UserNotification.create_with_limit(
            user=request.user,
            title="Заявка отправлена",
            message=f"Ваша заявка на '{notif}' отправлена",
            type=UserNotification.Type.SUCCESS,
        )

    messages.success(request, f"Запрос на подключение отправлен.")
    return redirect("accounts:services")


class NotificationsView(LoginRequiredMixin, ListView):
    template_name = "accounts/notifications.html"
    context_object_name = "notifications"

    def get_queryset(self):
        user = self.request.user

        # Получаем персональные + глобальные уведомления
        user_notifications = UserNotification.objects.filter(user=user)
        global_notifications = GlobalNotification.objects.all()

        # Помечаем персональные как прочитанные
        user_notifications.filter(is_read=False).update(is_read=True)

        # Объединяем
        all_notifications = list(global_notifications) + list(user_notifications)
        all_notifications.sort(key=lambda x: x.created_at, reverse=True)

        return all_notifications


# class RegisterView(CreateView):
#     form_class = UserCreationForm
#     template_name = 'accounts/register.html'
#     success_url = reverse_lazy("accounts:main")
#
#     def form_valid(self, form):
#         response = super().form_valid(form)
#         # Profile.objects.create(user=self.object) or signal
#         username = form.cleaned_data.get("username")
#         password = form.cleaned_data.get("password1")
#         user = authenticate(self.request, username=username, password=password)
#         login(request=self.request, user=user)
#         return response


# def redir(request):
#     return redirect("accounts:main")

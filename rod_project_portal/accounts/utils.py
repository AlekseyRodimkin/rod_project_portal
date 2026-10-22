from django.contrib.staticfiles import finders
from django.http import FileResponse, Http404
from django.db.models import Q
from calls.models import Friendship


def unread_notifications_count(request):
    """
    Контекстный процессор для подсчета кол-ва непрочитанных уведомлений
    Подключен в settings.py: TEMPLATES
    """
    if request.user.is_authenticated:
        count = request.user.notifications.filter(is_read=False).count()
    else:
        count = 0
    return {"unread_notifications_count": count}


def is_superuser(request):
    """
    Контекстный процессор для определения админа
    Подключен в settings.py: TEMPLATES
    """
    return {"user_is_admin": request.user.is_superuser}


def service_worker(request):
    """
    Отдаёт файл service worker по адресу /sw.js.

    Как работает: ищет js/sw.js в static-папках проекта, отдаёт его как
    JavaScript с заголовком Cache-Control: no-cache, чтобы браузер при каждой
    проверке брал свежую версию. Если файла нет — ответ 404.
    """
    path = finders.find("js/sw.js")  # ищет файл в ваших static-папках
    if not path:
        raise Http404("sw.js не найден")
    response = FileResponse(open(path, "rb"), content_type="application/javascript")
    response["Cache-Control"] = "no-cache"  # чтобы обновления подхватывались сразу
    return response


def profile_modal(request):
    """
    Контекстный процессор для окна профиля

    Как работает:
        - для неавторизованного пользователя ничего не добавляет
        - берёт все подтверждённые дружбы (ACCEPTED), где текущий пользователь
          либо инициатор (from_user), либо получатель (to_user)
        - из каждой связи выбирает собеседника, то есть второго участника
        - select_related подгружает профили (фото) одним запросом, без запроса на каждого друга

    Возвращает: {"profile_friends": [User, ...]}, список друзей для блока «Контакты»
    в окне профиля. Ключ доступен во всех шаблонах
    """
    user = request.user
    if not user.is_authenticated:
        return {}
    qs = Friendship.objects.filter(
        Q(from_user=user) | Q(to_user=user), status=Friendship.Status.ACCEPTED
    ).select_related("from_user__profile", "to_user__profile")
    return {"profile_friends": [f.to_user if f.from_user_id == user.id else f.from_user for f in qs]}

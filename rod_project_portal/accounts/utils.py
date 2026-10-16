from django.contrib.staticfiles import finders
from django.http import FileResponse, Http404


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

    Зачем: service worker управляет только страницами «внутри» своей папки.
    Из static/js/ он видел бы лишь адреса /static/js/..., а не весь сайт.
    Эта функция отдаёт тот же файл с корня (/sw.js), и охват — весь сайт.

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

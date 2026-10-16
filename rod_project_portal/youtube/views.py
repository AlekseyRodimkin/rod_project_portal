from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse, StreamingHttpResponse, HttpResponseBadRequest
from django.views import View
from django.views.generic import TemplateView
from accounts.models import UserNotification

from .services import (
    is_valid_youtube_url,
    get_stream_url,
    fetch_video_metadata,
    stream_generator,
)


class YoutubeView(LoginRequiredMixin, TemplateView):
    template_name = "youtube/live.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context["user_is_admin"] = user.is_superuser
        context["unread_count"] = UserNotification.objects.filter(
            user=self.request.user, is_read=False
        ).count()

        return context


class ValidateUrlView(View):
    """Эндпоинт валидации URL: /validate_url?url=..."""

    async def get(self, request, *args, **kwargs):
        url = request.GET.get("url", "")

        if not await is_valid_youtube_url(url=url):
            return JsonResponse({"detail": "Некорректная ссылка"}, status=400)

        return JsonResponse({"status": "ok"})


class GetLivePlayUrlView(View):
    """Возвращает JSON с URL для стриминга: /live_play?url=..."""

    async def get(self, request, *args, **kwargs):
        url = request.GET.get("url", "")
        if not url:
            return HttpResponseBadRequest("URL is required")

        # Если нужно отправить уведомление боту:
        # await send_bot_notif()

        stream_url = await get_stream_url(url)
        if not stream_url:
            return JsonResponse(
                {
                    "error_type": 404,
                    "error_message": "Не удалось получить поток",
                },
                status=404,
            )

        file_size, supports_range = await fetch_video_metadata(stream_url)
        content_type = "video/mp4"

        return JsonResponse(
            {
                "stream_url": stream_url,
                "content_type": content_type,
                "supports_range": supports_range,
                "file_size": file_size,
            }
        )


class StreamVideoView(View):
    """Стримит видео по полученному URL: /stream?stream_url=..."""

    async def get(self, request, *args, **kwargs):
        stream_url = request.GET.get("stream_url")
        if not stream_url:
            return HttpResponseBadRequest("Stream URL is required")

        file_size, supports_range = await fetch_video_metadata(stream_url)
        range_header = request.headers.get("Range")
        start, end = 0, file_size - 1 if file_size else None

        if range_header and supports_range:
            try:
                range_type, ranges = range_header.split("=")
                if range_type.strip() == "bytes":
                    start, end = ranges.split("-")
                    start = int(start)
                    end = int(end) if end else file_size - 1
            except Exception:
                pass

        headers = {
            "Accept-Ranges": "bytes",
            "Content-Type": "video/mp4",
        }

        if supports_range:
            headers["Content-Range"] = f"bytes {start}-{end}/{file_size}"
            status_code = 206
        else:
            status_code = 200

        response = StreamingHttpResponse(
            stream_generator(
                start=start,
                end=end,
                supports_range=supports_range,
                stream_url=stream_url,
            ),
            status=status_code,
            content_type="video/mp4",
        )

        for key, value in headers.items():
            response[key] = value

        return response

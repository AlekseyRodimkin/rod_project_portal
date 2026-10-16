from django.urls import path
from .views import YoutubeView, ValidateUrlView, GetLivePlayUrlView, StreamVideoView

app_name = "youtube"
urlpatterns = [
    path("youtube/", YoutubeView.as_view(), name="youtube"),
    path("validate_url", ValidateUrlView.as_view(), name="validate_url"),
    path("live_play", GetLivePlayUrlView.as_view(), name="live_play"),
    path("stream", StreamVideoView.as_view(), name="stream"),
]

from django.urls import path
from video_app.api.views import MetaVideoView, HLSPlaylistView, HLSSegmentView

urlpatterns = [
    path('video/', MetaVideoView.as_view(), name='metavideo'),
    path('video/<int:movie_id>/<str:resolution>/index.m3u8', HLSPlaylistView.as_view(), name='video-hls-playlist'),
    path('video/<int:movie_id>/<str:resolution>/<str:segment>/', HLSSegmentView.as_view(), name='video-hls-segment'),
]
import os
import re

from django.core.cache import cache
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import generics, permissions
from video_app.models import Video
from video_app.tasks import RESOLUTIONS, hls_dir, VIDEO_LIST_CACHE_KEY
from .serializers import VideoSerializer
from auth_app.api.authentication import CookieJWTAuthentication


def _resolve_thumbnail_urls(request, data):
    """Rewrite each video's server-relative thumbnail_url into an absolute URL for the current host."""
    for video in data:
        url = video.get('thumbnail_url')
        if url and not url.startswith(('http://', 'https://')):
            video['thumbnail_url'] = request.build_absolute_uri(url)
    return data


class  MetaVideoView(generics.ListAPIView):
    """
    API endpoint that returns metadata for a video file.
    Serialized results are cached in Redis (with host-independent, relative thumbnail URLs)
    and invalidated whenever a Video changes.
    """

    queryset = Video.objects.all()
    serializer_class = VideoSerializer
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request, *args, **kwargs):
        """Serve the video list from cache, falling back to the database on a cache miss."""
        data = cache.get(VIDEO_LIST_CACHE_KEY)
        if data is None:
            data = self.get_serializer(self.get_queryset(), many=True).data
            cache.set(VIDEO_LIST_CACHE_KEY, data)
        return Response(_resolve_thumbnail_urls(request, data))


class HLSPlaylistView(APIView):
    """
    API endpoint that returns the HLS master playlist (index.m3u8) for a given movie and resolution.
    """

    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, movie_id, resolution):
        get_object_or_404(Video, pk=movie_id)

        if resolution not in RESOLUTIONS:
            raise Http404("Unknown resolution.")

        manifest_path = os.path.join(hls_dir(movie_id, resolution), 'index.m3u8')
        if not os.path.isfile(manifest_path):
            raise Http404("Manifest not found.")

        return FileResponse(open(manifest_path, 'rb'), content_type='application/vnd.apple.mpegurl')


SEGMENT_NAME_RE = re.compile(r'^[A-Za-z0-9_-]+\.ts$')


class HLSSegmentView(APIView):
    """
    API endpoint that returns a single HLS video segment (.ts) for a given movie and resolution.
    """

    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, movie_id, resolution, segment):
        get_object_or_404(Video, pk=movie_id)

        if resolution not in RESOLUTIONS or not SEGMENT_NAME_RE.match(segment):
            raise Http404("Segment not found.")

        segment_path = os.path.join(hls_dir(movie_id, resolution), segment)
        if not os.path.isfile(segment_path):
            raise Http404("Segment not found.")

        return FileResponse(open(segment_path, 'rb'), content_type='video/MP2T')

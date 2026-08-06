import os
import re

from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework import generics, permissions
from video_app.models import Video
from video_app.tasks import RESOLUTIONS, hls_dir
from .serializers import VideoSerializer
from auth_app.api.authentication import CookieJWTAuthentication


class  MetaVideoView(generics.ListAPIView):
    """
    API endpoint that returns metadata for a video file.
    """

    queryset = Video.objects.all()
    serializer_class = VideoSerializer
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]


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

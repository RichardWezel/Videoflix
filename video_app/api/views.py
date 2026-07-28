from rest_framework.views import APIView
from rest_framework import generics, permissions
from video_app.models import Video
from .serializers import VideoSerializer


class  MetaVideoView(generics.ListAPIView):
    """
    API endpoint that returns metadata for a video file.
    """

    queryset = Video.objects.all()
    serializer_class = VideoSerializer
    permission_classes = [permissions.IsAuthenticated]

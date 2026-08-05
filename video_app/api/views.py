from rest_framework.views import APIView
from rest_framework import generics, permissions
from video_app.models import Video
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

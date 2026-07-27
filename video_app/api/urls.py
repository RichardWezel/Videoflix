from django.urls import path
from auth_app.api.views import MetaVideoView

urlpatterns = [
    path('video/', MetaVideoView.as_view(), name='metavideo'),
    
]
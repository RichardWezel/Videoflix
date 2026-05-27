from django.urls import path
from auth_app.api.views import RegisterView, ActivateView

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('activate/<str:uid>/<str:token>/', ActivateView.as_view(), name='activate'),
]
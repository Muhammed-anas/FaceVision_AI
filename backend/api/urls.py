from django.urls import path
from .views import CameraStreamAPI

urlpatterns = [
    path('camera/', CameraStreamAPI.as_view(), name='camera-stream'),
]

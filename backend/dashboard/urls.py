from django.urls import path
from .views import live_camera_view

urlpatterns = [
    path('live/', live_camera_view, name='live-camera'),
]

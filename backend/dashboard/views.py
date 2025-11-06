from django.shortcuts import render

def live_camera_view(request):
    return render(request, 'live_camera.html')

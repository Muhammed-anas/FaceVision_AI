import base64
import cv2
import numpy as np
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from deepface import DeepFace

class FaceRecognitionAPI(APIView):
    def post(self, request):
        try:
            image_data = request.data.get("image")

            if not image_data:
                return Response({"error": "No image provided"}, status=400)

            # Convert Base64 to OpenCV Image
            img_bytes = base64.b64decode(image_data)
            np_arr = np.frombuffer(img_bytes, np.uint8)
            frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

            # Analyze using DeepFace
            result = DeepFace.analyze(
                frame,
                actions=['age', 'gender', 'emotion'],
                enforce_detection=False
            )

            return Response({
                "age": result.get("age"),
                "gender": result.get("gender"),
                "emotion": result.get("dominant_emotion"),
            }, status=200)

        except Exception as e:
            return Response({"error": str(e)}, status=500)

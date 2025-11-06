# backend/api/views.py - COMBINED VERSION (no need for separate AI service)

import cv2
import base64
import numpy as np
from rest_framework.views import APIView
from rest_framework.response import Response
from deepface import DeepFace
import logging

logger = logging.getLogger(__name__)

class CameraStreamAPI(APIView):
    """Combined endpoint - handles camera AND AI analysis in one place"""
    
    def get(self, request):
        """Capture from local webcam (for testing)"""
        try:
            cap = cv2.VideoCapture(0)
            if not cap.isOpened():
                return Response({"error": "Camera not accessible"}, status=500)

            ret, frame = cap.read()
            cap.release()

            if not ret:
                return Response({"error": "Failed to capture frame"}, status=500)

            # Analyze directly
            result = self._analyze_face(frame)
            return Response(result)

        except Exception as e:
            logger.error(f"Camera GET error: {str(e)}")
            return Response({"error": str(e)}, status=500)

    def post(self, request):
        """Accept image from browser and analyze directly"""
        try:
            image_b64 = request.data.get('image')

            if not image_b64:
                return Response({
                    "error": "No image provided",
                    "received_keys": list(request.data.keys()) if isinstance(request.data, dict) else None
                }, status=400)

            # Decode image
            try:
                img_bytes = base64.b64decode(image_b64)
                np_arr = np.frombuffer(img_bytes, np.uint8)
                frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
                
                if frame is None:
                    return Response({"error": "Invalid image data"}, status=400)
                
                logger.info(f"Image decoded: {frame.shape}")
                
            except Exception as e:
                logger.error(f"Image decode error: {str(e)}")
                return Response({
                    "error": "Image decode error",
                    "detail": str(e)
                }, status=400)

            # Analyze the face
            result = self._analyze_face(frame)
            return Response(result)

        except Exception as e:
            logger.error(f"POST error: {str(e)}", exc_info=True)
            return Response({
                "error": "Internal server error",
                "detail": str(e)
            }, status=500)

    def _analyze_face(self, frame):
        """Analyze face using DeepFace"""
        try:
            logger.info("Starting DeepFace analysis...")
            
            result = DeepFace.analyze(
                frame,
                actions=['age', 'gender', 'emotion'],
                enforce_detection=False,
                silent=True
            )
            
            logger.info(f"DeepFace analysis complete")
            
            # Handle result
            if not result:
                return {
                    "success": True,
                    "data": {
                        "error": "No face detected",
                        "age": None,
                        "gender": None,
                        "emotion": None
                    }
                }

            # Get first face
            face_data = result[0] if isinstance(result, list) else result
            
            age = face_data.get('age')
            gender = face_data.get('dominant_gender', 'Unknown')
            emotion = face_data.get('dominant_emotion', 'Unknown')
            
            logger.info(f"Results - Age: {age}, Gender: {gender}, Emotion: {emotion}")
            
            return {
                "success": True,
                "data": {
                    "age": age,
                    "gender": gender,
                    "emotion": emotion
                }
            }
            
        except Exception as e:
            logger.error(f"DeepFace error: {str(e)}")
            return {
                "success": True,
                "data": {
                    "error": f"Analysis failed: {str(e)}",
                    "age": None,
                    "gender": None,
                    "emotion": None
                }
            }
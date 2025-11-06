import base64
import cv2
import numpy as np
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from deepface import DeepFace
import logging

logger = logging.getLogger(__name__)

class FaceRecognitionAPI(APIView):
    def post(self, request):
        try:
            image_data = request.data.get("image")

            if not image_data:
                logger.warning("No image data in request")
                return Response({"error": "No image provided"}, status=400)

            # Convert Base64 to OpenCV Image
            try:
                img_bytes = base64.b64decode(image_data)
                np_arr = np.frombuffer(img_bytes, np.uint8)
                frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
                
                if frame is None:
                    logger.error("Failed to decode image")
                    return Response({"error": "Invalid image data - could not decode"}, status=400)
                
                logger.info(f"Image decoded successfully: {frame.shape}")
                
            except Exception as e:
                logger.error(f"Image decode error: {str(e)}")
                return Response({
                    "error": "Image decode error",
                    "detail": str(e)
                }, status=400)

            # Analyze using DeepFace
            logger.info("Starting DeepFace analysis...")
            try:
                result = DeepFace.analyze(
                    frame,
                    actions=['age', 'gender', 'emotion'],
                    enforce_detection=False,
                    silent=True
                )
                logger.info(f"DeepFace analysis complete: {type(result)}")
                
            except Exception as e:
                logger.error(f"DeepFace analysis error: {str(e)}")
                return Response({
                    "error": "Face analysis failed",
                    "detail": str(e),
                    "age": None,
                    "gender": None,
                    "emotion": None
                }, status=200)

            # Handle the result - DeepFace returns a LIST
            if not result:
                logger.warning("DeepFace returned empty result")
                return Response({
                    "error": "No face detected in image",
                    "age": None,
                    "gender": None,
                    "emotion": None
                }, status=200)

            # Get first face if multiple detected
            if isinstance(result, list):
                if len(result) == 0:
                    logger.warning("DeepFace returned empty list")
                    return Response({
                        "error": "No face detected",
                        "age": None,
                        "gender": None,
                        "emotion": None
                    }, status=200)
                face_data = result[0]
            else:
                face_data = result

            logger.info(f"Face data keys: {face_data.keys()}")

            # Extract data with proper key handling
            age = face_data.get('age')
            dominant_gender = face_data.get('dominant_gender', 'Unknown')
            dominant_emotion = face_data.get('dominant_emotion', 'Unknown')

            logger.info(f"Extracted - Age: {age}, Gender: {dominant_gender}, Emotion: {dominant_emotion}")

            return Response({
                "age": age,
                "gender": dominant_gender,
                "emotion": dominant_emotion,
            }, status=200)

        except Exception as e:
            logger.error(f"Unexpected error in FaceRecognitionAPI: {str(e)}", exc_info=True)
            return Response({
                "error": "Server error",
                "detail": str(e)
            }, status=500)
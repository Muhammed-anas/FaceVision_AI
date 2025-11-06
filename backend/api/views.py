import cv2
import base64
import requests
from rest_framework.views import APIView
from rest_framework.response import Response
import logging

logger = logging.getLogger(__name__)

AI_SERVICE_URL = "http://127.0.0.1:8001/api/recognize/"

class CameraStreamAPI(APIView):
    def get(self, request):
        """Capture from local webcam and send to AI service"""
        try:
            cap = cv2.VideoCapture(0)

            if not cap.isOpened():
                return Response({"error": "Camera not accessible"}, status=500)

            ret, frame = cap.read()
            cap.release()

            if not ret:
                return Response({"error": "Failed to capture frame"}, status=500)

            # Convert frame to Base64
            _, buffer = cv2.imencode('.jpg', frame)
            base64_img = base64.b64encode(buffer).decode('utf-8')

            # Send to AI service
            try:
                response = requests.post(AI_SERVICE_URL, json={"image": base64_img}, timeout=10)
                response.raise_for_status()
                ai_result = response.json()
                
                return Response({
                    "success": True,
                    "data": ai_result
                })
            except requests.ConnectionError:
                return Response({
                    "error": "AI service not running on port 8001",
                    "detail": "Please start: cd ai_service && python manage.py runserver 8001"
                }, status=502)
            except Exception as e:
                return Response({
                    "error": f"AI service error: {str(e)}"
                }, status=502)

        except Exception as e:
            logger.error(f"Camera GET error: {str(e)}")
            return Response({"error": str(e)}, status=500)

    def post(self, request):
        """Accept image from browser and forward to AI service"""
        try:
            image_b64 = None
            timestamp = request.data.get('timestamp')

            # Get image from request
            if isinstance(request.data, dict):
                image_b64 = request.data.get('image')
                
                if image_b64:
                    try:
                        decoded = base64.b64decode(image_b64)
                        if len(decoded) == 0:
                            return Response({
                                "error": "Empty image data"
                            }, status=400)
                        
                        logger.info(f"Received image: {len(decoded)} bytes")
                    except Exception as e:
                        return Response({
                            "error": "Invalid base64 image data",
                            "detail": str(e)
                        }, status=400)

            elif 'image' in request.FILES:
                uploaded = request.FILES['image']
                img_bytes = uploaded.read()
                image_b64 = base64.b64encode(img_bytes).decode('utf-8')

            if not image_b64:
                return Response({
                    "error": "No image provided",
                    "received_keys": list(request.data.keys()) if isinstance(request.data, dict) else None
                }, status=400)

            # Forward to AI service
            try:
                logger.info(f"Sending to AI service: {AI_SERVICE_URL}")
                response = requests.post(
                    AI_SERVICE_URL, 
                    json={"image": image_b64}, 
                    timeout=15
                )
                
                logger.info(f"AI service responded: {response.status_code}")
                
                # Log first 500 chars of response for debugging
                response_text = response.text[:500]
                logger.debug(f"AI response preview: {response_text}")
                
                if response.status_code != 200:
                    return Response({
                        "error": f"AI service returned {response.status_code}",
                        "detail": response_text
                    }, status=502)
                
                ai_result = response.json()
                
                # Validate response structure
                if not isinstance(ai_result, dict):
                    return Response({
                        "error": "Invalid AI service response format",
                        "received_type": str(type(ai_result))
                    }, status=502)
                
                return Response({
                    "success": True,
                    "data": ai_result
                })
                
            except requests.Timeout:
                logger.error("AI service timeout")
                return Response({
                    "error": "AI service timeout (took more than 15 seconds)",
                    "detail": "DeepFace processing may be slow. Try again."
                }, status=504)
                
            except requests.ConnectionError as e:
                logger.error(f"Cannot connect to AI service: {str(e)}")
                return Response({
                    "error": "Cannot connect to AI service on port 8001",
                    "detail": "Make sure AI service is running: cd ai_service && python manage.py runserver 8001",
                    "technical_detail": str(e)
                }, status=502)
                
            except requests.RequestException as e:
                logger.error(f"AI service request error: {str(e)}")
                return Response({
                    "error": f"AI service communication error",
                    "detail": str(e)
                }, status=502)
                
            except ValueError as e:
                logger.error(f"Invalid JSON from AI service: {str(e)}")
                return Response({
                    "error": "Invalid JSON response from AI service",
                    "detail": str(e),
                    "response_preview": response.text[:500]
                }, status=502)

        except Exception as e:
            logger.error(f"Backend API error: {str(e)}", exc_info=True)
            return Response({
                "error": "Internal server error",
                "detail": str(e)
            }, status=500)
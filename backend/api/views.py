import cv2
import base64
import requests
from rest_framework.views import APIView
from rest_framework.response import Response

AI_SERVICE_URL = "http://127.0.0.1:8001/api/recognize/"

class CameraStreamAPI(APIView):
    def get(self, request):
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
            response = requests.post(AI_SERVICE_URL, json={"image": base64_img})
            ai_result = response.json()

            return Response({
                "success": True,
                "data": ai_result
            })

        except Exception as e:
            return Response({"error": str(e)}, status=500)

    def post(self, request):
        """Accept an image from the browser (base64 string in JSON or an uploaded file)
        and forward it to the AI service. Returns the AI service result.
        """
        try:
            image_b64 = None
            timestamp = None

            # Case 1: JSON payload with 'image' (base64 string)
            if isinstance(request.data, dict):
                image_b64 = request.data.get('image')
                timestamp = request.data.get('timestamp')  # Optional, for debugging
                
                # Validate base64 content
                if image_b64:
                    try:
                        # Test if it's valid base64
                        base64.b64decode(image_b64)
                    except Exception as e:
                        return Response({
                            "error": "Invalid base64 image data",
                            "detail": str(e)
                        }, status=400)

            # Case 2: multipart upload with file field 'image'
            elif 'image' in request.FILES:
                uploaded = request.FILES['image']
                img_bytes = uploaded.read()
                image_b64 = base64.b64encode(img_bytes).decode('utf-8')

            if not image_b64:
                return Response({
                    "error": "No image provided",
                    "received_keys": list(request.data.keys()) if isinstance(request.data, dict) else None,
                    "timestamp": timestamp
                }, status=400)

            # Forward to AI service
            # Add timeout to AI service call
            try:
                response = requests.post(AI_SERVICE_URL, json={"image": image_b64}, timeout=5)
                response.raise_for_status()  # Raises error for 4xx/5xx
            except requests.Timeout:
                return Response({"error": "AI service timeout"}, status=504)
            except requests.RequestException as e:
                return Response({"error": f"AI service error: {str(e)}"}, status=502)

            try:
                ai_result = response.json()
            except ValueError:
                return Response({
                    "error": "Invalid JSON from AI service",
                    "status_code": response.status_code,
                    "text": response.text[:500]  # Truncate long responses
                }, status=502)

            if not isinstance(ai_result, dict):
                return Response({
                    "error": "Unexpected AI service response format",
                    "received": str(type(ai_result))
                }, status=502)

            return Response({
                "success": True,
                "data": ai_result
            })

        except Exception as e:
            return Response({"error": str(e)}, status=500)

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from auth_app.api.serializers import RegisterSerializer
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes

class RegisterView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()

            # Token generieren
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
        
            # Hier kommt später der E-Mail-Versand hin
            return Response({"user": {
                                "id": user.id,
                                "email": user.email,
                             },
                             "token": token
                            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
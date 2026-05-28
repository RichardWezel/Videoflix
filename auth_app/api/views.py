from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from auth_app.api.serializers import RegisterSerializer, LoginSerializer
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth import get_user_model
from auth_app.api.utils import send_activation_email

class RegisterView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            send_activation_email(user, uid, token)
            return Response({"user": {
                                "id": user.id,
                                "email": user.email,
                             },
                             "token": token
                            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ActivateView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def get(self, _request, uid, token):
        User = get_user_model()
        try:
            user_id = force_str(urlsafe_base64_decode(uid))
            user = User.objects.get(pk=user_id)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return Response({"message": "Invalid activation link"}, status=status.HTTP_400_BAD_REQUEST)

        if not default_token_generator.check_token(user, token):
            return Response({"message": "Activation link is invalid or has expired"}, status=status.HTTP_400_BAD_REQUEST)

        if user.is_active:
            return Response({"message": "Account is already activated"}, status=status.HTTP_200_OK)

        user.is_active = True
        user.account_activated = True
        user.save()
        return Response({"message": "Account successfully activated!"}, status=status.HTTP_200_OK)

class LoginView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    serializer_class = LoginSerializer

    def post(self, request):
        try:
            serializer = self.serializer_class(data=request.data)
            serializer.is_valid(raise_exception=True)

            refresh = serializer.validated_data["refresh"]
            access = serializer.validated_data["access"]
            user = serializer.validated_data["user"]

            response = Response({
                "detail": "Login successfully",
                "user": {
                    "id": user.id,
                    "username": user.email
                }
            }, status=status.HTTP_200_OK)

            response.set_cookie(
                key='access_token',
                value=str(access),
                httponly=True,
                secure=False,
                samesite='Lax'
            )
            response.set_cookie(
                key='refresh_token',
                value=str(refresh),
                httponly=True,
                secure=False,
                samesite='Lax'
            )

            return response

        except Exception as e:
            return Response({"error": "Invalid username or password"}, status=status.HTTP_401_UNAUTHORIZED)
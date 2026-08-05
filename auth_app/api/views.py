from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth import get_user_model

from auth_app.api.serializers import RegisterSerializer, LoginSerializer, PasswordResetSerializer, PasswordResetConfirmSerializer
from auth_app.api.utils import send_activation_email, send_password_reset_email
from auth_app.api.permissions import HasRefreshTokenCookie
from auth_app.api.authentication import CookieJWTAuthentication

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError


class RegisterView(APIView):
    """View to handle user registration and send activation email."""
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        """Handle user registration and send activation email."""
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
    """View to handle account activation via email link."""
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def get(self, _request, uid, token):
        """Handle account activation by validating the token and activating the user account."""
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
    """View to handle user login and return JWT tokens in cookies."""
    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    serializer_class = LoginSerializer

    def post(self, request):
        """Handle user login and return JWT tokens in cookies."""
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
        
class LogoutView(APIView):
    """View to handle user logout and token blacklisting."""
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [permissions.IsAuthenticated, HasRefreshTokenCookie]

    def post(self, request):
        """Handle user logout by blacklisting the refresh token and deleting cookies."""

        refresh_token = request.COOKIES.get('refresh_token')
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except TokenError:
            pass

        response = Response(
            {"detail": "Logout successful! All tokens will be deleted. Refresh token is now invalid."},
            status=status.HTTP_200_OK
        )
        response.delete_cookie('access_token')
        response.delete_cookie('refresh_token')
        return response

class TokenRefreshView(APIView):
    """View to handle JWT token refresh."""
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        """Handle token refresh by validating the refresh token and returning a new access token."""
        refresh_token = request.COOKIES.get('refresh_token')
        if not refresh_token:
            return Response({"error": "Refresh token is missing"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            token = RefreshToken(refresh_token)
            new_access_token = str(token.access_token)

            response = Response({
                "detail": "Token refreshed",
                "access": new_access_token
            }, status=status.HTTP_200_OK)
            response.set_cookie(
                key='access_token',
                value=new_access_token,
                httponly=True,
                secure=False,
                samesite='Lax'
            )
            return response

        except TokenError:
            return Response({"error": "Invalid refresh token"}, status=status.HTTP_401_UNAUTHORIZED)

class PasswordResetView(APIView):
    """View to handle password reset requests."""
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        """Handle password reset request by sending an email with a reset link."""
        serializer = PasswordResetSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        email = serializer.validated_data.get('email')
        User = get_user_model()
        try:
            user = User.objects.get(email=email)
            if not user:
                return Response({"error": "User with this email does not exist"}, status=status.HTTP_404_NOT_FOUND)
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            send_password_reset_email(user, uid, token)
            return Response({"detail": "An email has been sent to reset your password."}, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return Response({"error": "User with this email does not exist"}, status=status.HTTP_404_NOT_FOUND)
        
class PasswordResetConfirmView(APIView):
    """View to handle password reset confirmation."""
    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    serializer_class = PasswordResetConfirmSerializer 

    def post(self, request, uid, token):
        """Handle password reset confirmation by validating the token and setting a new password."""
        User = get_user_model()
        try:
            user_id = force_str(urlsafe_base64_decode(uid))
            user = User.objects.get(pk=user_id)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return Response({"message": "Invalid password reset link"}, status=status.HTTP_400_BAD_REQUEST)

        if not default_token_generator.check_token(user, token):
            return Response({"message": "Password reset link is invalid or has expired"}, status=status.HTTP_400_BAD_REQUEST)

        serializer = self.serializer_class(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        new_password = serializer.validated_data.get('new_password')
        user.set_password(new_password)
        user.save()
        return Response({"message": "Password has been reset successfully!"}, status=status.HTTP_200_OK)
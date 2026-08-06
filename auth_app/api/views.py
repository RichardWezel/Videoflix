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


def _set_cookie(response, key, value):
    """Helper function to set a single httponly auth cookie."""
    response.set_cookie(key=key, value=str(value), httponly=True, secure=False, samesite='Lax')


def set_auth_cookies(response, access_token, refresh_token):
    """Helper function to set access and refresh token cookies."""
    _set_cookie(response, 'access_token', access_token)
    _set_cookie(response, 'refresh_token', refresh_token)
    return response


def create_access_cookie_response(access_token, message="Token refreshed"):
    """Helper function to return a response with an access token cookie."""
    response = Response({"detail": message, "access": access_token}, status=status.HTTP_200_OK)
    _set_cookie(response, 'access_token', access_token)
    return response


def decode_and_get_user(uid):
    """Helper function to decode uid and retrieve user."""
    User = get_user_model()
    try:
        user_id = force_str(urlsafe_base64_decode(uid))
        return User.objects.get(pk=user_id), None
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        return None, Response({"message": "Invalid link"}, status=status.HTTP_400_BAD_REQUEST)


def send_password_reset_if_exists(email):
    """Send password reset email if a user with the given email exists."""
    User = get_user_model()
    try:
        user = User.objects.get(email=email)
        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        send_password_reset_email(user, uid, token)
    except User.DoesNotExist:
        pass


def validate_token(user, token, link_type="activation"):
    """Helper function to validate token."""
    if not default_token_generator.check_token(user, token):
        msg = f"{link_type.capitalize()} link is invalid or has expired"
        return False, Response({"message": msg}, status=status.HTTP_400_BAD_REQUEST)
    return True, None


class RegisterView(APIView):
    """View to handle user registration and send activation email."""
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        """Handle user registration and send activation email."""
        serializer = RegisterSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        user = serializer.save()
        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        send_activation_email(user, uid, token)
        data = {"user": {"id": user.id, "email": user.email}, "token": token}
        return Response(data, status=status.HTTP_201_CREATED)


class ActivateView(APIView):
    """View to handle account activation via email link."""
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    @staticmethod
    def _activate(user):
        user.is_active = True
        user.account_activated = True
        user.save()
        return Response({"message": "Account successfully activated!"}, status=status.HTTP_200_OK)

    def get(self, _request, uid, token):
        """Activate account by token after resolving user via helper functions."""
        user, error_response = decode_and_get_user(uid)
        if error_response:
            return Response({"message": "Invalid activation link"}, status=status.HTTP_400_BAD_REQUEST)
        _is_valid, error_response = validate_token(user, token, "activation")
        if error_response:
            return error_response
        if user.is_active:
            return Response({"message": "Account is already activated"}, status=status.HTTP_200_OK)
        return self._activate(user)

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
            data = serializer.validated_data
            user = data["user"]
            detail = {"detail": "Login successfully", "user": {"id": user.id, "username": user.email}}
            response = Response(detail, status=status.HTTP_200_OK)
            set_auth_cookies(response, data["access"], data["refresh"])
            return response
        except Exception:
            return Response({"error": "Invalid username or password"}, status=status.HTTP_401_UNAUTHORIZED)
        
class LogoutView(APIView):
    """View to handle user logout and token blacklisting."""
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [permissions.IsAuthenticated, HasRefreshTokenCookie]

    @staticmethod
    def _blacklist_refresh_token(refresh_token):
        try:
            RefreshToken(refresh_token).blacklist()
        except TokenError:
            pass

    def post(self, request):
        """Handle user logout by blacklisting the refresh token and deleting cookies."""
        self._blacklist_refresh_token(request.COOKIES.get('refresh_token'))
        detail = "Logout successful! All tokens will be deleted. Refresh token is now invalid."
        response = Response({"detail": detail}, status=status.HTTP_200_OK)
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
            new_access = str(token.access_token)
            return create_access_cookie_response(new_access, message="Token refreshed")
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

        send_password_reset_if_exists(serializer.validated_data.get('email'))
        return Response({"detail": "If an account with this email exists, a password reset email will be sent."},
                        status=status.HTTP_200_OK)
        
class PasswordResetConfirmView(APIView):
    """View to handle password reset confirmation."""
    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    serializer_class = PasswordResetConfirmSerializer

    @staticmethod
    def _set_new_password(user, password):
        user.set_password(password)
        user.save()

    def post(self, request, uid, token):
        """Handle password reset confirmation by validating the token and setting a new password."""
        user, error_response = decode_and_get_user(uid)
        if error_response:
            return Response({"message": "Invalid password reset link"}, status=status.HTTP_400_BAD_REQUEST)
        _is_valid, error_response = validate_token(user, token, "password reset")
        if error_response:
            return error_response
        serializer = self.serializer_class(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        self._set_new_password(user, serializer.validated_data.get('new_password'))
        return Response({"message": "Password has been reset successfully!"}, status=status.HTTP_200_OK)
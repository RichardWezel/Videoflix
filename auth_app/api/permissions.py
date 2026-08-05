from rest_framework.permissions import BasePermission


class HasRefreshTokenCookie(BasePermission):
    """Grants access only if a refresh_token cookie is present on the request."""

    message = "Refresh token cookie is required"

    def has_permission(self, request, view):
        return bool(request.COOKIES.get('refresh_token'))

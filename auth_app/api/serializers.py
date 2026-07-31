from django.contrib.auth.password_validation import validate_password
from django.contrib.auth import authenticate

from auth_app.models import CustomUser

from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

class RegisterSerializer(serializers.ModelSerializer):
    """Serializer for user registration."""

    confirmed_password = serializers.CharField(write_only=True)

    class Meta:
        model = CustomUser
        fields = ( 'email', 'password', 'confirmed_password')
        extra_kwargs = {'password': {'write_only': True}}   
    
    def validate_password(self, value):
        """Validate the password using Django's built-in password validators."""
        validate_password(value)
        return value

    def validate_email(self, value):
        """Validate the email field to ensure it is unique and properly formatted."""
        if CustomUser.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        if not value:
            raise serializers.ValidationError("Email is required.")
        if not isinstance(value, str) or "@" not in value:
            raise serializers.ValidationError("Enter a valid email address.")
        return value

    def validate(self, data):
        """Validate that the password and confirmed_password fields match."""
        if data['password'] != data['confirmed_password']:
            raise serializers.ValidationError("Passwords do not match.")
        return data

    def create(self, validated_data):
        """Create a new user instance with the validated data."""
        validated_data.pop('confirmed_password')
        user = CustomUser.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            is_active=False
        )
        return user

class LoginSerializer(serializers.Serializer):
    """Serializer for user login."""
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    class Meta:
        model = CustomUser
        fields = ( 'email', 'password')
        extra_kwargs = {'password': {'write_only': True}}  

    def validate(self, data):
        """
        Validate the email and password fields.
        Authenticate the user and return a JWT token if valid.
        """
        
        user = authenticate(email=data['email'], password=data['password'])
        if not user:
            raise serializers.ValidationError("Invalid email or password.")
        if not user.is_active:
            raise serializers.ValidationError("Account is not activated yet.")

        refresh = RefreshToken.for_user(user)
        return {
            "user": user,
            "refresh": refresh,
            "access": refresh.access_token,
        }

class PasswordResetSerializer(serializers.Serializer):
    """Serializer for password reset request."""
    email = serializers.EmailField()

    class Meta:
        model = CustomUser
        fields = ('email',)

    def validate_email(self, value):
        """Validate the email field to ensure it exists in the database."""
        if not CustomUser.objects.filter(email=value).exists():
            raise serializers.ValidationError("No user is associated with this email address.")
        return value

class PasswordResetConfirmSerializer(serializers.Serializer):
    """Serializer for confirming password reset."""
    new_password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    class Meta:
        model = CustomUser
        fields = ('new_password', 'confirmed_password')

    def validate_new_password(self, value):
        """Validate the new password using Django's built-in password validators."""
        validate_password(value)
        return value

    def validate_confirm_password(self, value):
        """Validate that the confirm_password field matches the new_password field."""
        new_password = self.initial_data.get('new_password')
        if new_password and value != new_password:
            raise serializers.ValidationError("Passwords do not match.")
        return value

    def validate(self, data):
        """Validate that the new_password and confirm_password fields match."""
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError("Passwords do not match.")
        return data
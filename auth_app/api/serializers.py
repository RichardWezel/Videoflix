from rest_framework import serializers
from auth_app.models import CustomUser
from django.contrib.auth.password_validation import validate_password

class RegisterSerializer(serializers.ModelSerializer):
    confirmed_password = serializers.CharField(write_only=True)

    class Meta:
        model = CustomUser
        fields = ( 'email', 'password', 'confirmed_password')
        extra_kwargs = {'password': {'write_only': True}}   
    
    def validate_password(self, value):
        validate_password(value)
        return value

    def validate(self, data):
        if data['password'] != data['confirmed_password']:
            raise serializers.ValidationError("Passwords do not match.")
        return data

    def create(self, validated_data):
        validated_data.pop('confirmed_password')
        user = CustomUser.objects.create_user(  # ← create_user nutzen!
            email=validated_data['email'],
            password=validated_data['password'],
            is_active=False
        )
        return user
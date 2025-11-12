"""
Serializers for accounts app.
"""
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import User, Role


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model."""
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    
    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name', 'phone',
            'role', 'role_display', 'is_active', 'mfa_enabled',
            'date_joined', 'last_login'
        ]
        read_only_fields = ['id', 'date_joined', 'last_login']


class UserCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating users."""
    password = serializers.CharField(write_only=True, min_length=8)
    
    class Meta:
        model = User
        fields = ['email', 'password', 'first_name', 'last_name', 'phone', 'role']
    
    def create(self, validated_data):
        """Create user with hashed password."""
        password = validated_data.pop('password')
        user = User.objects.create_user(password=password, **validated_data)
        return user


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Custom token serializer with user data."""
    # Use email field instead of username
    username_field = 'email'
    
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['role'] = user.role
        token['email'] = user.email
        return token
    
    def validate(self, attrs):
        # Map 'email' to 'username' for parent validation
        # Since USERNAME_FIELD is 'email', Django will use email as username
        if 'email' in attrs and 'username' not in attrs:
            attrs['username'] = attrs['email']
        data = super().validate(attrs)
        data['user'] = UserSerializer(self.user).data
        return data

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
    
    def validate_role(self, value):
        """Prevent users from changing their own role (unless admin)."""
        request = self.context.get('request')
        if request and request.user:
            # If updating self and not admin, don't allow role change
            if self.instance and self.instance == request.user:
                if not getattr(request.user, 'is_admin', False):
                    # Non-admin users cannot change their own role
                    if value != self.instance.role:
                        raise serializers.ValidationError(
                            'You cannot change your own role. Contact an administrator.'
                        )
        return value
    
    def validate(self, attrs):
        """Additional validation for user updates."""
        request = self.context.get('request')
        if request and request.user and self.instance:
            # If updating self and not admin, don't allow certain changes
            if self.instance == request.user:
                if not getattr(request.user, 'is_admin', False):
                    # Non-admin users cannot deactivate themselves
                    if 'is_active' in attrs and attrs['is_active'] is False:
                        raise serializers.ValidationError({
                            'is_active': 'You cannot deactivate your own account.'
                        })
        return attrs


class UserCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating users."""
    password = serializers.CharField(write_only=True, min_length=8)
    
    class Meta:
        model = User
        fields = ['email', 'password', 'first_name', 'last_name', 'phone', 'role']
    
    def create(self, validated_data):
        """Create user with hashed password."""
        password = validated_data.pop('password')
        request = self.context.get('request')
        
        # If created by admin, user is active immediately
        # Otherwise, user is inactive (pending approval)
        is_active = request and request.user and request.user.is_admin
        
        user = User.objects.create_user(
            password=password,
            is_active=is_active,
            **validated_data
        )
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
        
        # Ensure user is available and add user data to response
        if not hasattr(self, 'user') or self.user is None:
            raise serializers.ValidationError('User authentication failed.')
        
        # Serialize user data and add to response
        user_serializer = UserSerializer(self.user)
        data['user'] = user_serializer.data
        return data


class PasswordResetRequestSerializer(serializers.Serializer):
    """Serializer for password reset request."""
    email = serializers.EmailField(required=True)
    
    def validate_email(self, value):
        """Check if user exists."""
        if not User.objects.filter(email=value).exists():
            # Don't reveal if email exists for security
            pass
        return value


class PasswordResetConfirmSerializer(serializers.Serializer):
    """Serializer for password reset confirmation."""
    token = serializers.CharField(required=True)
    password = serializers.CharField(required=True, min_length=8, write_only=True)
    
    def validate_token(self, value):
        """Validate reset token format."""
        if '.' not in value:
            raise serializers.ValidationError('Invalid token format.')
        return value

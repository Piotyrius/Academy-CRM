"""
Serializers for accounts app.
"""
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from cryptography.fernet import InvalidToken
from .models import User, Role
from .mfa import verify_totp


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
    
    def _get_target_organization(self):
        """
        Determine which organization the new user should belong to.
        
        Prefer the request's organization (set by TenantMiddleware / mixins),
        falling back to the creator's organization if available.
        """
        request = self.context.get('request')
        if not request:
            return None
        
        organization = getattr(request, 'organization', None)
        if organization is None and getattr(request, 'user', None):
            organization = getattr(request.user, 'organization', None)
        return organization
    
    def validate(self, attrs):
        """
        Enforce subscription user limits when creating users for an organization.
        """
        attrs = super().validate(attrs)
        request = self.context.get('request')
        organization = self._get_target_organization()

        # For a strictly multi-tenant system, require an organization for new users,
        # except when created by a superuser (global admin).
        if (not organization) and not (request and getattr(request.user, 'is_superuser', False)):
            raise serializers.ValidationError({
                'non_field_errors': ['Organization is required when creating a user.']
            })

        if organization and hasattr(organization, 'can_add_user'):
            allowed, message = organization.can_add_user()
            if not allowed:
                # Attach error to non-field errors so it's clearly visible
                raise serializers.ValidationError({'non_field_errors': [message]})
        return attrs
    
    def create(self, validated_data):
        """Create user with hashed password."""
        password = validated_data.pop('password')
        request = self.context.get('request')
        
        # If created by admin, user is active immediately
        # Otherwise, user is inactive (pending approval)
        is_active = request and request.user and request.user.is_admin
        
        # Attach organization from context if available
        organization = self._get_target_organization()
        if organization:
            validated_data.setdefault('organization', organization)
        
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
        """
        Validate credentials and return JWT data with embedded user info.

        Additionally, handle cases where the user's `mfa_secret` cannot be
        decrypted (e.g. after `SECRET_KEY` rotation or data corruption) so that
        login never returns a 500 due to `InvalidToken`.
        """
        # Map 'email' to 'username' for parent validation.
        # Since USERNAME_FIELD is 'email', Django will use email as username.
        if 'email' in attrs and 'username' not in attrs:
            attrs['username'] = attrs['email']

        try:
            data = super().validate(attrs)
        except InvalidToken:
            # If decrypting `mfa_secret` fails while loading the user, clear
            # the secret for this account and retry once so we avoid a 500 and
            # let the user re-enable MFA later.
            email = attrs.get('email') or attrs.get('username')
            if email:
                # Use queryset.update() so we don't have to load the model
                # instance (which would try to decrypt the invalid value again).
                User.objects.filter(email=email).update(
                    mfa_secret=None,
                    mfa_enabled=False,
                )
                try:
                    data = super().validate(attrs)
                except InvalidToken:
                    raise serializers.ValidationError(
                        'User authentication failed due to invalid MFA data. '
                        'Please contact support.'
                    )
            else:
                raise serializers.ValidationError('User authentication failed.')

        # Ensure user is available
        if not hasattr(self, 'user') or self.user is None:
            raise serializers.ValidationError('User authentication failed.')

        # Enforce MFA if enabled for this user.
        if getattr(self.user, 'mfa_enabled', False):
            mfa_code = attrs.get('mfa_code')
            if not mfa_code:
                raise serializers.ValidationError(
                    {'mfa_code': 'MFA code is required for this account.'}
                )
            # `mfa_secret` is encrypted at rest; accessing it decrypts via fernet_fields.
            secret = getattr(self.user, 'mfa_secret', None)
            if not secret or not verify_totp(secret, str(mfa_code).strip()):
                raise serializers.ValidationError(
                    {'mfa_code': 'Invalid or expired MFA code.'}
                )

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


class TokenBlacklistRequestSerializer(serializers.Serializer):
    """Serializer for token blacklist request (logout)."""
    refresh = serializers.CharField(required=True, help_text="Refresh token to blacklist")


class TokenBlacklistResponseSerializer(serializers.Serializer):
    """Serializer for token blacklist response."""
    detail = serializers.CharField(help_text="Success message")

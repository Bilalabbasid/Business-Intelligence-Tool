from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from .models import User


class UserRegistrationSerializer(serializers.ModelSerializer):
    """
    Serializer for user registration
    """
    password = serializers.CharField(
        write_only=True,
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    password_confirm = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'}
    )
    
    class Meta:
        model = User
        fields = (
            'username', 'email', 'password', 'password_confirm',
            'first_name', 'last_name', 'role', 'branch_id', 'phone_number'
        )
        extra_kwargs = {
            'username': {'required': True},
            'email': {'required': True},
            'first_name': {'required': False},
            'last_name': {'required': False},
            'phone_number': {'required': False},
            'branch_id': {'required': False},
        }
    
    def validate(self, attrs):
        """
        Validate the registration data
        """
        # Check password confirmation
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({
                'password_confirm': 'Password confirmation does not match.'
            })
        
        # Validate role-branch relationship
        role = attrs.get('role')
        branch_id = attrs.get('branch_id')
        
        if role in [User.MANAGER, User.STAFF] and not branch_id:
            raise serializers.ValidationError({
                'branch_id': f'{role} must be assigned to a branch.'
            })
        
        if role in [User.SUPER_ADMIN, User.ANALYST] and branch_id:
            raise serializers.ValidationError({
                'branch_id': f'{role} should not be assigned to a specific branch.'
            })
        
        return attrs
    
    def create(self, validated_data):
        """
        Create a new user instance
        """
        validated_data.pop('password_confirm', None)
        password = validated_data.pop('password')
        
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        
        return user


class UserLoginSerializer(serializers.Serializer):
    """
    Serializer for user login
    """
    username = serializers.CharField(required=True)
    password = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'}
    )
    
    def validate(self, attrs):
        """
        Validate login credentials
        """
        username = attrs.get('username')
        password = attrs.get('password')
        
        if username and password:
            # Authenticate user
            user = authenticate(
                request=self.context.get('request'),
                username=username,
                password=password
            )
            
            if not user:
                raise serializers.ValidationError(
                    'Invalid username or password.',
                    code='authorization'
                )
            
            if not user.is_active:
                raise serializers.ValidationError(
                    'User account is disabled.',
                    code='authorization'
                )
            
            attrs['user'] = user
            return attrs
        else:
            raise serializers.ValidationError(
                'Must provide username and password.',
                code='authorization'
            )


class UserProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for user profile (read-only and update)
    """
    full_name = serializers.CharField(read_only=True)
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    
    class Meta:
        model = User
        fields = (
            'id', 'username', 'email', 'first_name', 'last_name', 'full_name',
            'role', 'role_display', 'branch_id', 'phone_number', 'profile_picture',
            'is_active', 'date_joined', 'last_login', 'created_at', 'updated_at'
        )
        read_only_fields = (
            'id', 'username', 'role', 'branch_id', 'is_active',
            'date_joined', 'last_login', 'created_at', 'updated_at'
        )


class UserUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating user profile
    """
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'phone_number', 'profile_picture')
        
    def update(self, instance, validated_data):
        """
        Update user profile
        """
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


class PasswordChangeSerializer(serializers.Serializer):
    """
    Serializer for changing password
    """
    current_password = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'}
    )
    new_password = serializers.CharField(
        required=True,
        write_only=True,
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    new_password_confirm = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'}
    )
    
    def validate(self, attrs):
        """
        Validate password change data
        """
        user = self.context['user']
        current_password = attrs['current_password']
        new_password = attrs['new_password']
        new_password_confirm = attrs['new_password_confirm']
        
        # Check current password
        if not user.check_password(current_password):
            raise serializers.ValidationError({
                'current_password': 'Current password is incorrect.'
            })
        
        # Check new password confirmation
        if new_password != new_password_confirm:
            raise serializers.ValidationError({
                'new_password_confirm': 'New password confirmation does not match.'
            })
        
        return attrs
    
    def save(self):
        """
        Change the user's password
        """
        user = self.context['user']
        new_password = self.validated_data['new_password']
        user.set_password(new_password)
        user.save()
        return user


class UserListSerializer(serializers.ModelSerializer):
    """
    Serializer for listing users (admin use)
    """
    full_name = serializers.CharField(read_only=True)
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    
    class Meta:
        model = User
        fields = (
            'id', 'username', 'email', 'full_name', 'role', 'role_display',
            'branch_id', 'is_active', 'date_joined', 'last_login'
        )


class UserCreateByAdminSerializer(serializers.ModelSerializer):
    """
    Serializer for admin to create users
    """
    password = serializers.CharField(
        write_only=True,
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    
    class Meta:
        model = User
        fields = (
            'username', 'email', 'password', 'first_name', 'last_name',
            'role', 'branch_id', 'phone_number', 'is_active'
        )
        extra_kwargs = {
            'username': {'required': True},
            'email': {'required': True},
            'role': {'required': True},
        }
    
    def validate(self, attrs):
        """
        Validate admin user creation data
        """
        role = attrs.get('role')
        branch_id = attrs.get('branch_id')
        
        # Validate role-branch relationship
        if role in [User.MANAGER, User.STAFF] and not branch_id:
            raise serializers.ValidationError({
                'branch_id': f'{role} must be assigned to a branch.'
            })
        
        if role in [User.SUPER_ADMIN, User.ANALYST] and branch_id:
            raise serializers.ValidationError({
                'branch_id': f'{role} should not be assigned to a specific branch.'
            })
        
        return attrs
    
    def create(self, validated_data):
        """
        Create user by admin
        """
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        
        # Set created_by to the requesting user (admin)
        request = self.context.get('request')
        if request and request.user:
            user.created_by = request.user
        
        user.save()
        return user
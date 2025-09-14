from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import GenericAPIView, RetrieveUpdateAPIView
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import login
from django.db import transaction
import logging

from .models import User, UserSession
from .serializers import (
    UserRegistrationSerializer, UserLoginSerializer, UserProfileSerializer,
    UserUpdateSerializer, PasswordChangeSerializer, UserListSerializer,
    UserCreateByAdminSerializer
)
from .permissions import IsSuperAdmin, IsManagerOrAbove, IsOwnerOrAdmin

logger = logging.getLogger(__name__)


class UserRegistrationView(GenericAPIView):
    """
    API view for user registration
    """
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        """
        Register a new user
        """
        serializer = self.get_serializer(data=request.data)
        
        if serializer.is_valid():
            try:
                with transaction.atomic():
                    user = serializer.save()
                    
                    # Log successful registration
                    logger.info(f"New user registered: {user.username} ({user.email})")
                    
                    # Generate JWT tokens
                    refresh = RefreshToken.for_user(user)
                    access_token = refresh.access_token
                    
                    # Create user session
                    self._create_user_session(user, request)
                    
                    return Response({
                        'message': 'User registered successfully',
                        'user': UserProfileSerializer(user).data,
                        'tokens': {
                            'access': str(access_token),
                            'refresh': str(refresh)
                        }
                    }, status=status.HTTP_201_CREATED)
                    
            except Exception as e:
                logger.error(f"Error during user registration: {str(e)}")
                return Response({
                    'error': 'Registration failed. Please try again.'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def _create_user_session(self, user, request):
        """
        Create a user session record
        """
        try:
            UserSession.objects.create(
                user=user,
                session_key=request.session.session_key or 'web_session',
                ip_address=self._get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:500]
            )
        except Exception as e:
            logger.warning(f"Failed to create user session: {str(e)}")
    
    def _get_client_ip(self, request):
        """
        Get client IP address from request
        """
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class CustomTokenObtainPairView(TokenObtainPairView):
    """
    Custom JWT token obtain view with additional user data
    """
    
    def post(self, request, *args, **kwargs):
        """
        Login user and return tokens with user data
        """
        serializer = UserLoginSerializer(data=request.data, context={'request': request})
        
        if serializer.is_valid():
            user = serializer.validated_data['user']
            
            # Update last login
            user.last_login = timezone.now()
            user.save(update_fields=['last_login'])
            
            # Generate tokens
            refresh = RefreshToken.for_user(user)
            access_token = refresh.access_token
            
            # Create user session
            self._create_user_session(user, request)
            
            # Log successful login
            logger.info(f"User logged in: {user.username}")
            
            return Response({
                'message': 'Login successful',
                'user': UserProfileSerializer(user).data,
                'tokens': {
                    'access': str(access_token),
                    'refresh': str(refresh)
                }
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def _create_user_session(self, user, request):
        """
        Create a user session record
        """
        try:
            # Deactivate old sessions
            UserSession.objects.filter(user=user, is_active=True).update(is_active=False)
            
            # Create new session
            UserSession.objects.create(
                user=user,
                session_key=request.session.session_key or 'jwt_session',
                ip_address=self._get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:500]
            )
        except Exception as e:
            logger.warning(f"Failed to create user session: {str(e)}")
    
    def _get_client_ip(self, request):
        """
        Get client IP address from request
        """
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class UserProfileView(RetrieveUpdateAPIView):
    """
    API view for user profile (get and update)
    """
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        return self.request.user
    
    def get_serializer_class(self):
        if self.request.method == 'PATCH' or self.request.method == 'PUT':
            return UserUpdateSerializer
        return UserProfileSerializer
    
    def retrieve(self, request, *args, **kwargs):
        """
        Get current user profile
        """
        user = self.get_object()
        serializer = UserProfileSerializer(user)
        
        return Response({
            'user': serializer.data,
            'permissions': self._get_user_permissions(user)
        })
    
    def _get_user_permissions(self, user):
        """
        Get user permissions based on role
        """
        permissions_map = {
            User.SUPER_ADMIN: {
                'can_access_all_branches': True,
                'can_manage_users': True,
                'can_view_reports': True,
                'can_manage_settings': True,
                'can_export_data': True,
            },
            User.MANAGER: {
                'can_access_all_branches': False,
                'can_manage_users': True,  # Only for their branch
                'can_view_reports': True,
                'can_manage_settings': False,
                'can_export_data': True,
            },
            User.ANALYST: {
                'can_access_all_branches': True,  # Read-only access
                'can_manage_users': False,
                'can_view_reports': True,
                'can_manage_settings': False,
                'can_export_data': True,
            },
            User.STAFF: {
                'can_access_all_branches': False,
                'can_manage_users': False,
                'can_view_reports': False,  # Limited reports only
                'can_manage_settings': False,
                'can_export_data': False,
            },
        }
        
        return permissions_map.get(user.role, {})


class PasswordChangeView(GenericAPIView):
    """
    API view for changing password
    """
    serializer_class = PasswordChangeSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        """
        Change user password
        """
        serializer = self.get_serializer(
            data=request.data,
            context={'user': request.user}
        )
        
        if serializer.is_valid():
            try:
                user = serializer.save()
                logger.info(f"Password changed for user: {user.username}")
                
                return Response({
                    'message': 'Password changed successfully'
                }, status=status.HTTP_200_OK)
                
            except Exception as e:
                logger.error(f"Error changing password: {str(e)}")
                return Response({
                    'error': 'Failed to change password'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LogoutView(APIView):
    """
    API view for user logout
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        """
        Logout user and blacklist refresh token
        """
        try:
            # Get refresh token from request
            refresh_token = request.data.get('refresh')
            
            if refresh_token:
                # Blacklist the refresh token
                token = RefreshToken(refresh_token)
                token.blacklist()
            
            # Deactivate user sessions
            UserSession.objects.filter(
                user=request.user,
                is_active=True
            ).update(is_active=False)
            
            logger.info(f"User logged out: {request.user.username}")
            
            return Response({
                'message': 'Logout successful'
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error during logout: {str(e)}")
            return Response({
                'error': 'Logout failed'
            }, status=status.HTTP_400_BAD_REQUEST)


# Admin-only views
class UserListView(GenericAPIView):
    """
    API view for listing users (admin only)
    """
    serializer_class = UserListSerializer
    permission_classes = [IsSuperAdmin]
    
    def get(self, request):
        """
        List all users (super admin only)
        """
        users = User.objects.all().order_by('-date_joined')
        
        # Filter by role if specified
        role = request.query_params.get('role')
        if role:
            users = users.filter(role=role)
        
        # Filter by branch if specified
        branch_id = request.query_params.get('branch_id')
        if branch_id:
            users = users.filter(branch_id=branch_id)
        
        # Filter by active status
        is_active = request.query_params.get('is_active')
        if is_active is not None:
            users = users.filter(is_active=is_active.lower() == 'true')
        
        serializer = self.get_serializer(users, many=True)
        
        return Response({
            'users': serializer.data,
            'total_count': users.count()
        })


class UserCreateByAdminView(GenericAPIView):
    """
    API view for admin to create users
    """
    serializer_class = UserCreateByAdminSerializer
    permission_classes = [IsSuperAdmin]
    
    def post(self, request):
        """
        Create user by admin
        """
        serializer = self.get_serializer(data=request.data, context={'request': request})
        
        if serializer.is_valid():
            try:
                user = serializer.save()
                logger.info(f"User created by admin {request.user.username}: {user.username}")
                
                return Response({
                    'message': 'User created successfully',
                    'user': UserProfileSerializer(user).data
                }, status=status.HTTP_201_CREATED)
                
            except Exception as e:
                logger.error(f"Error creating user by admin: {str(e)}")
                return Response({
                    'error': 'Failed to create user'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def user_sessions_view(request):
    """
    Get current user's active sessions
    """
    sessions = UserSession.objects.filter(
        user=request.user,
        is_active=True
    ).order_by('-last_activity')
    
    sessions_data = []
    for session in sessions:
        sessions_data.append({
            'id': session.id,
            'ip_address': session.ip_address,
            'user_agent': session.user_agent[:100] + '...' if len(session.user_agent) > 100 else session.user_agent,
            'created_at': session.created_at,
            'last_activity': session.last_activity,
        })
    
    return Response({
        'sessions': sessions_data,
        'total_count': len(sessions_data)
    })


from django.utils import timezone
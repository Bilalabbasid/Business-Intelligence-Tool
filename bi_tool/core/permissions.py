from rest_framework import permissions
from .models import User


class IsSuperAdmin(permissions.BasePermission):
    """
    Permission class to allow access only to super admins
    """
    
    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.is_super_admin()
        )


class IsManagerOrAbove(permissions.BasePermission):
    """
    Permission class to allow access to managers and super admins
    """
    
    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.role in [User.SUPER_ADMIN, User.MANAGER]
        )


class IsAnalystOrAbove(permissions.BasePermission):
    """
    Permission class to allow access to analysts and above
    """
    
    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.role in [User.SUPER_ADMIN, User.MANAGER, User.ANALYST]
        )


class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Permission class to allow access to the owner of the object or admins
    """
    
    def has_object_permission(self, request, view, obj):
        # Super admins can access everything
        if request.user.is_super_admin():
            return True
        
        # Users can access their own objects
        if hasattr(obj, 'user') and obj.user == request.user:
            return True
        
        # If the object is the user themselves
        if obj == request.user:
            return True
        
        return False


class CanAccessBranch(permissions.BasePermission):
    """
    Permission class to check if user can access specific branch data
    """
    
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        
        # Get branch_id from URL parameters or query parameters
        branch_id = view.kwargs.get('branch_id') or request.query_params.get('branch_id')
        
        if not branch_id:
            return True  # No specific branch restriction
        
        return request.user.can_access_branch(branch_id)


class ReadOnlyForAnalysts(permissions.BasePermission):
    """
    Permission class that allows read-only access for analysts
    """
    
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        
        # Super admins and managers can do everything
        if request.user.role in [User.SUPER_ADMIN, User.MANAGER]:
            return True
        
        # Analysts can only read
        if request.user.is_analyst():
            return request.method in permissions.SAFE_METHODS
        
        # Staff have very limited access
        return False
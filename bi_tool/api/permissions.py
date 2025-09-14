from rest_framework.permissions import BasePermission
from django.db.models import Q
from core.models import User


class BaseRBACPermission(BasePermission):
    """
    Base permission class for Role-Based Access Control
    """
    
    def has_permission(self, request, view):
        """
        Check if the user has permission to access the view
        """
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Allow superusers to access everything
        if request.user.is_superuser:
            return True
        
        # Check role-specific permissions
        return self.has_role_permission(request, view)
    
    def has_role_permission(self, request, view):
        """
        Override in subclasses to implement role-specific permissions
        """
        return True
    
    def has_object_permission(self, request, view, obj):
        """
        Check if the user has permission to access a specific object
        """
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Allow superusers to access everything
        if request.user.is_superuser:
            return True
        
        return self.has_role_object_permission(request, view, obj)
    
    def has_role_object_permission(self, request, view, obj):
        """
        Override in subclasses to implement role-specific object permissions
        """
        return True
    
    def get_user_branches(self, user):
        """
        Get the branches a user can access based on their role
        """
        if user.role == User.SUPER_ADMIN:
            return None  # Access to all branches
        elif user.role == User.MANAGER:
            # Managers can access their own branch
            return [user.branch_id] if user.branch_id else []
        elif user.role in [User.ANALYST, User.STAFF]:
            # Analysts and Staff can access their assigned branch
            return [user.branch_id] if user.branch_id else []
        return []


class BranchPermission(BaseRBACPermission):
    """
    Permission class for Branch model operations
    """
    
    def has_role_permission(self, request, view):
        """
        Check role-based permissions for branch operations
        """
        role = request.user.role
        action = view.action if hasattr(view, 'action') else None
        
        # SUPER_ADMIN: Full access
        if role == User.SUPER_ADMIN:
            return True
        
        # MANAGER: Can view and update their own branch
        elif role == User.MANAGER:
            if action in ['list', 'retrieve', 'partial_update', 'update']:
                return True
            return False
        
        # ANALYST: Read-only access to their branch
        elif role == User.ANALYST:
            if action in ['list', 'retrieve']:
                return True
            return False
        
        # STAFF: Read-only access to their branch
        elif role == User.STAFF:
            if action in ['retrieve']:
                return True
            return False
        
        return False
    
    def has_role_object_permission(self, request, view, obj):
        """
        Check object-level permissions for branch operations
        """
        user_branches = self.get_user_branches(request.user)
        
        # Super admin can access all branches
        if user_branches is None:
            return True
        
        # Check if the branch is in user's accessible branches
        return str(obj.branch_id) in [str(b) for b in user_branches]


class SalesPermission(BaseRBACPermission):
    """
    Permission class for Sales model operations
    """
    
    def has_role_permission(self, request, view):
        """
        Check role-based permissions for sales operations
        """
        role = request.user.role
        action = view.action if hasattr(view, 'action') else None
        
        # SUPER_ADMIN: Full access
        if role == User.SUPER_ADMIN:
            return True
        
        # MANAGER: Full access to their branch sales
        elif role == User.MANAGER:
            return True
        
        # ANALYST: Read-only access to their branch sales
        elif role == User.ANALYST:
            if action in ['list', 'retrieve']:
                return True
            return False
        
        # STAFF: Can create sales and view their own sales
        elif role == User.STAFF:
            if action in ['list', 'retrieve', 'create']:
                return True
            elif action in ['update', 'partial_update']:
                # Staff can only edit sales they created
                return True  # Will be handled in object permission
            return False
        
        return False
    
    def has_role_object_permission(self, request, view, obj):
        """
        Check object-level permissions for sales operations
        """
        user_branches = self.get_user_branches(request.user)
        role = request.user.role
        action = view.action if hasattr(view, 'action') else None
        
        # Super admin can access all sales
        if user_branches is None:
            return True
        
        # Check if the sale is from user's accessible branches
        if str(obj.branch.branch_id) not in [str(b) for b in user_branches]:
            return False
        
        # Additional checks for STAFF role
        if role == User.STAFF:
            if action in ['update', 'partial_update', 'destroy']:
                # Staff can only edit/delete their own sales
                return obj.served_by == request.user
        
        return True


class InventoryPermission(BaseRBACPermission):
    """
    Permission class for Inventory model operations
    """
    
    def has_role_permission(self, request, view):
        """
        Check role-based permissions for inventory operations
        """
        role = request.user.role
        action = view.action if hasattr(view, 'action') else None
        
        # SUPER_ADMIN: Full access
        if role == User.SUPER_ADMIN:
            return True
        
        # MANAGER: Full access to their branch inventory
        elif role == User.MANAGER:
            return True
        
        # ANALYST: Read-only access to their branch inventory
        elif role == User.ANALYST:
            if action in ['list', 'retrieve']:
                return True
            return False
        
        # STAFF: Can view and update stock levels
        elif role == User.STAFF:
            if action in ['list', 'retrieve', 'partial_update']:
                return True
            return False
        
        return False
    
    def has_role_object_permission(self, request, view, obj):
        """
        Check object-level permissions for inventory operations
        """
        user_branches = self.get_user_branches(request.user)
        role = request.user.role
        
        # Super admin can access all inventory
        if user_branches is None:
            return True
        
        # Check if the inventory item is from user's accessible branches
        if str(obj.branch.branch_id) not in [str(b) for b in user_branches]:
            return False
        
        # Additional restrictions for STAFF
        if role == User.STAFF:
            # Staff can only update specific fields (handled in serializer)
            return True
        
        return True


class CustomerPermission(BaseRBACPermission):
    """
    Permission class for Customer model operations
    """
    
    def has_role_permission(self, request, view):
        """
        Check role-based permissions for customer operations
        """
        role = request.user.role
        action = view.action if hasattr(view, 'action') else None
        
        # SUPER_ADMIN: Full access
        if role == User.SUPER_ADMIN:
            return True
        
        # MANAGER: Full access to their branch customers
        elif role == User.MANAGER:
            return True
        
        # ANALYST: Read-only access to their branch customers
        elif role == User.ANALYST:
            if action in ['list', 'retrieve']:
                return True
            return False
        
        # STAFF: Can view and create customers, limited updates
        elif role == User.STAFF:
            if action in ['list', 'retrieve', 'create', 'partial_update']:
                return True
            return False
        
        return False
    
    def has_role_object_permission(self, request, view, obj):
        """
        Check object-level permissions for customer operations
        """
        user_branches = self.get_user_branches(request.user)
        role = request.user.role
        
        # Super admin can access all customers
        if user_branches is None:
            return True
        
        # Check if the customer's preferred branch is accessible
        if obj.preferred_branch and str(obj.preferred_branch.branch_id) not in [str(b) for b in user_branches]:
            return False
        
        return True


class StaffPerformancePermission(BaseRBACPermission):
    """
    Permission class for StaffPerformance model operations
    """
    
    def has_role_permission(self, request, view):
        """
        Check role-based permissions for staff performance operations
        """
        role = request.user.role
        action = view.action if hasattr(view, 'action') else None
        
        # SUPER_ADMIN: Full access
        if role == User.SUPER_ADMIN:
            return True
        
        # MANAGER: Full access to their branch staff performance
        elif role == User.MANAGER:
            return True
        
        # ANALYST: Read-only access to their branch staff performance
        elif role == User.ANALYST:
            if action in ['list', 'retrieve']:
                return True
            return False
        
        # STAFF: Can view their own performance only
        elif role == User.STAFF:
            if action in ['list', 'retrieve']:
                return True
            return False
        
        return False
    
    def has_role_object_permission(self, request, view, obj):
        """
        Check object-level permissions for staff performance operations
        """
        user_branches = self.get_user_branches(request.user)
        role = request.user.role
        
        # Super admin can access all performance records
        if user_branches is None:
            return True
        
        # Check if the performance record is from user's accessible branches
        if str(obj.branch.branch_id) not in [str(b) for b in user_branches]:
            return False
        
        # Additional checks for STAFF role
        if role == User.STAFF:
            # Staff can only view their own performance
            return obj.staff == request.user
        
        return True


class AuditLogPermission(BaseRBACPermission):
    """
    Permission class for AuditLog model operations
    """
    
    def has_role_permission(self, request, view):
        """
        Check role-based permissions for audit log operations
        """
        role = request.user.role
        action = view.action if hasattr(view, 'action') else None
        
        # SUPER_ADMIN: Full access
        if role == User.SUPER_ADMIN:
            return True
        
        # MANAGER: Can view audit logs for their branch
        elif role == User.MANAGER:
            if action in ['list', 'retrieve']:
                return True
            return False
        
        # ANALYST: Can view audit logs for their branch
        elif role == User.ANALYST:
            if action in ['list', 'retrieve']:
                return True
            return False
        
        # STAFF: No access to audit logs
        elif role == User.STAFF:
            return False
        
        return False
    
    def has_role_object_permission(self, request, view, obj):
        """
        Check object-level permissions for audit log operations
        """
        user_branches = self.get_user_branches(request.user)
        
        # Super admin can access all audit logs
        if user_branches is None:
            return True
        
        # Check if the audit log is from user's accessible branches
        return str(obj.branch_id) in [str(b) for b in user_branches] if obj.branch_id else True


class ReadOnlyPermission(BaseRBACPermission):
    """
    Permission class for read-only access
    """
    
    def has_role_permission(self, request, view):
        """
        Allow only read operations
        """
        action = view.action if hasattr(view, 'action') else None
        return action in ['list', 'retrieve']


class ManagerOnlyPermission(BaseRBACPermission):
    """
    Permission class that allows access only to managers and above
    """
    
    def has_role_permission(self, request, view):
        """
        Allow access only to managers and super admins
        """
        return request.user.role in [User.SUPER_ADMIN, User.MANAGER]


class SuperAdminOnlyPermission(BaseRBACPermission):
    """
    Permission class that allows access only to super admins
    """
    
    def has_role_permission(self, request, view):
        """
        Allow access only to super admins
        """
        return request.user.role == User.SUPER_ADMIN


class BranchFilterMixin:
    """
    Mixin to filter querysets based on user's branch access
    """
    
    def filter_queryset_by_branch(self, request, queryset):
        """
        Filter queryset based on user's branch access
        """
        if request.user.is_superuser or request.user.role == User.SUPER_ADMIN:
            return queryset
        
        # Get user's accessible branches
        user_branches = []
        if request.user.role == User.MANAGER:
            user_branches = [request.user.branch_id] if request.user.branch_id else []
        elif request.user.role in [User.ANALYST, User.STAFF]:
            user_branches = [request.user.branch_id] if request.user.branch_id else []
        
        if not user_branches:
            return queryset.none()
        
        # Determine the branch field name based on the model
        if hasattr(queryset.model, 'branch'):
            return queryset.filter(branch__branch_id__in=user_branches)
        elif hasattr(queryset.model, 'preferred_branch'):
            return queryset.filter(preferred_branch__branch_id__in=user_branches)
        elif hasattr(queryset.model, 'branch_id'):
            return queryset.filter(branch_id__in=user_branches)
        
        return queryset


class IsOwnerOrReadOnly(BasePermission):
    """
    Custom permission to only allow owners of an object to edit it.
    """
    
    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed for any request
        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            return True
        
        # Write permissions are only allowed to the owner of the object
        if hasattr(obj, 'created_by'):
            return obj.created_by == request.user
        elif hasattr(obj, 'staff'):
            return obj.staff == request.user
        elif hasattr(obj, 'served_by'):
            return obj.served_by == request.user
        
        return False


class DynamicPermissionMixin:
    """
    Mixin to provide dynamic permission classes based on action
    """
    
    def get_permissions(self):
        """
        Return the list of permission classes based on the action
        """
        permission_classes = self.permission_classes
        
        if hasattr(self, 'permission_classes_by_action'):
            permission_classes = self.permission_classes_by_action.get(
                self.action, self.permission_classes
            )
        
        return [permission() for permission in permission_classes]
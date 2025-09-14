"""
Role-Based Access Control (RBAC) and authorization permissions.
"""

from typing import Dict, List, Optional, Set, Any
from functools import wraps
from django.http import HttpRequest
from django.core.exceptions import PermissionDenied
from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView
from django.utils import timezone

from .models import User, AuditLog
from .auth import JWTAuthenticator


class RolePermissions:
    """Role-based permission definitions."""
    
    ROLE_PERMISSIONS = {
        'SUPER_ADMIN': {
            'resources': ['*'],
            'actions': ['*'],
            'branches': ['*'],
            'special_permissions': [
                'manage_users',
                'manage_roles',
                'view_audit_logs',
                'export_audit_logs',
                'manage_security_config',
                'rotate_encryption_keys',
                'manage_backups',
                'system_admin',
            ]
        },
        'SECURITY_ADMIN': {
            'resources': ['users', 'audit_logs', 'security_config', 'encryption_keys'],
            'actions': ['read', 'create', 'update', 'delete'],
            'branches': ['*'],
            'special_permissions': [
                'manage_users',
                'view_audit_logs',
                'export_audit_logs',
                'manage_security_config',
                'rotate_encryption_keys',
            ]
        },
        'ETL_ADMIN': {
            'resources': ['etl_jobs', 'data_sources', 'warehouses', 'dq_rules'],
            'actions': ['read', 'create', 'update', 'delete', 'execute'],
            'branches': ['*'],
            'special_permissions': [
                'manage_etl',
                'manage_data_quality',
                'export_raw_data',
            ]
        },
        'MANAGER': {
            'resources': ['dashboards', 'reports', 'analytics', 'users'],
            'actions': ['read', 'create', 'update'],
            'branches': ['branch_scoped'],
            'special_permissions': [
                'view_all_branch_data',
                'export_reports',
                'manage_team_users',
            ]
        },
        'ANALYST': {
            'resources': ['dashboards', 'reports', 'analytics'],
            'actions': ['read', 'create', 'update'],
            'branches': ['branch_scoped'],
            'special_permissions': [
                'create_reports',
                'export_data',
            ]
        },
        'STAFF': {
            'resources': ['dashboards', 'reports'],
            'actions': ['read'],
            'branches': ['branch_scoped'],
            'special_permissions': []
        },
        'VIEWER': {
            'resources': ['dashboards'],
            'actions': ['read'],
            'branches': ['branch_scoped'],
            'special_permissions': []
        }
    }
    
    # Resource-specific permissions
    RESOURCE_PERMISSIONS = {
        'users': {
            'create': ['SUPER_ADMIN', 'SECURITY_ADMIN', 'MANAGER'],
            'read': ['SUPER_ADMIN', 'SECURITY_ADMIN', 'MANAGER', 'ANALYST'],
            'update': ['SUPER_ADMIN', 'SECURITY_ADMIN', 'MANAGER'],
            'delete': ['SUPER_ADMIN', 'SECURITY_ADMIN'],
        },
        'audit_logs': {
            'read': ['SUPER_ADMIN', 'SECURITY_ADMIN'],
            'export': ['SUPER_ADMIN', 'SECURITY_ADMIN'],
        },
        'dashboards': {
            'create': ['SUPER_ADMIN', 'MANAGER', 'ANALYST'],
            'read': ['*'],  # All authenticated users
            'update': ['SUPER_ADMIN', 'MANAGER', 'ANALYST'],
            'delete': ['SUPER_ADMIN', 'MANAGER'],
        },
        'reports': {
            'create': ['SUPER_ADMIN', 'MANAGER', 'ANALYST'],
            'read': ['SUPER_ADMIN', 'MANAGER', 'ANALYST', 'STAFF'],
            'update': ['SUPER_ADMIN', 'MANAGER', 'ANALYST'],
            'delete': ['SUPER_ADMIN', 'MANAGER'],
            'export': ['SUPER_ADMIN', 'MANAGER', 'ANALYST'],
        },
        'etl_jobs': {
            'create': ['SUPER_ADMIN', 'ETL_ADMIN'],
            'read': ['SUPER_ADMIN', 'ETL_ADMIN', 'MANAGER'],
            'update': ['SUPER_ADMIN', 'ETL_ADMIN'],
            'delete': ['SUPER_ADMIN', 'ETL_ADMIN'],
            'execute': ['SUPER_ADMIN', 'ETL_ADMIN'],
        },
        'dq_rules': {
            'create': ['SUPER_ADMIN', 'ETL_ADMIN'],
            'read': ['SUPER_ADMIN', 'ETL_ADMIN', 'MANAGER'],
            'update': ['SUPER_ADMIN', 'ETL_ADMIN'],
            'delete': ['SUPER_ADMIN', 'ETL_ADMIN'],
        },
        'pii_data': {
            'read': ['SUPER_ADMIN'],
            'export': ['SUPER_ADMIN'],
        }
    }
    
    @classmethod
    def has_role_permission(cls, user_role: str, resource: str, action: str) -> bool:
        """Check if role has permission for resource action."""
        role_perms = cls.ROLE_PERMISSIONS.get(user_role, {})
        
        # Check wildcard permissions
        if '*' in role_perms.get('resources', []) and '*' in role_perms.get('actions', []):
            return True
        
        # Check specific resource permissions
        if resource in role_perms.get('resources', []):
            return action in role_perms.get('actions', []) or '*' in role_perms.get('actions', [])
        
        # Check resource-specific permissions
        resource_perms = cls.RESOURCE_PERMISSIONS.get(resource, {})
        action_roles = resource_perms.get(action, [])
        
        return user_role in action_roles or '*' in action_roles
    
    @classmethod
    def has_special_permission(cls, user_role: str, permission: str) -> bool:
        """Check if role has special permission."""
        role_perms = cls.ROLE_PERMISSIONS.get(user_role, {})
        return permission in role_perms.get('special_permissions', [])
    
    @classmethod
    def get_user_permissions(cls, user: User) -> Dict[str, Any]:
        """Get all permissions for a user."""
        role_perms = cls.ROLE_PERMISSIONS.get(user.role, {})
        return {
            'role': user.role,
            'resources': role_perms.get('resources', []),
            'actions': role_perms.get('actions', []),
            'branches': user.allowed_branches or [user.branch_id],
            'special_permissions': role_perms.get('special_permissions', []),
            'resource_scopes': user.resource_scopes,
        }


class BranchAccessControl:
    """Branch-based access control utilities."""
    
    @staticmethod
    def has_branch_access(user: User, branch_id: str) -> bool:
        """Check if user has access to specific branch."""
        # Super admin has access to all branches
        if user.role == 'SUPER_ADMIN':
            return True
        
        # Check user's primary branch
        if user.branch_id == 'ALL' or user.branch_id == branch_id:
            return True
        
        # Check allowed branches list
        return branch_id in user.allowed_branches
    
    @staticmethod
    def filter_data_by_branch(user: User, queryset, branch_field='branch_id'):
        """Filter queryset based on user's branch access."""
        if user.role == 'SUPER_ADMIN' or user.branch_id == 'ALL':
            return queryset
        
        # Filter by user's branches
        user_branches = [user.branch_id] + user.allowed_branches
        return queryset.filter(**{f'{branch_field}__in': user_branches})
    
    @staticmethod
    def get_accessible_branches(user: User) -> List[str]:
        """Get list of branches accessible to user."""
        if user.role == 'SUPER_ADMIN' or user.branch_id == 'ALL':
            return ['ALL']
        
        branches = [user.branch_id] if user.branch_id != 'ALL' else []
        branches.extend(user.allowed_branches)
        return list(set(branches))


class SecurityPermission(BasePermission):
    """Base DRF permission class with RBAC."""
    
    def has_permission(self, request: Request, view: APIView) -> bool:
        """Check if user has permission to access the view."""
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Get resource and action from view
        resource = getattr(view, 'required_resource', None)
        action = self.get_action_from_request(request)
        
        if not resource:
            return True  # No specific resource requirement
        
        # Check role-based permission
        has_permission = RolePermissions.has_role_permission(
            request.user.role, resource, action
        )
        
        if not has_permission:
            # Log unauthorized access attempt
            AuditLog.objects.create(
                user=request.user,
                action='UNAUTHORIZED_ACCESS',
                severity='HIGH',
                resource_type=resource,
                description=f'Unauthorized access attempt to {resource}:{action}',
                ip_address=self.get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                success=False,
            )
            return False
        
        return True
    
    def has_object_permission(self, request: Request, view: APIView, obj) -> bool:
        """Check object-level permissions."""
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Check branch access if object has branch_id
        if hasattr(obj, 'branch_id'):
            return BranchAccessControl.has_branch_access(request.user, obj.branch_id)
        
        return True
    
    def get_action_from_request(self, request: Request) -> str:
        """Get action from HTTP method."""
        method_action_map = {
            'GET': 'read',
            'POST': 'create',
            'PUT': 'update',
            'PATCH': 'update',
            'DELETE': 'delete',
        }
        return method_action_map.get(request.method.upper(), 'read')
    
    def get_client_ip(self, request: Request) -> str:
        """Get client IP address from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class AdminPermission(SecurityPermission):
    """Permission for admin-only resources."""
    
    def has_permission(self, request: Request, view: APIView) -> bool:
        if not super().has_permission(request, view):
            return False
        
        admin_roles = ['SUPER_ADMIN', 'SECURITY_ADMIN']
        return request.user.role in admin_roles


class BranchScopedPermission(SecurityPermission):
    """Permission with branch scoping."""
    
    def has_object_permission(self, request: Request, view: APIView, obj) -> bool:
        if not super().has_object_permission(request, view, obj):
            return False
        
        # Additional branch checking
        if hasattr(obj, 'branch_id'):
            if not BranchAccessControl.has_branch_access(request.user, obj.branch_id):
                AuditLog.objects.create(
                    user=request.user,
                    action='UNAUTHORIZED_ACCESS',
                    severity='HIGH',
                    resource_type=getattr(view, 'required_resource', 'unknown'),
                    resource_id=str(getattr(obj, 'id', '')),
                    description=f'Branch access denied for {obj.branch_id}',
                    ip_address=self.get_client_ip(request),
                    success=False,
                )
                return False
        
        return True


class PIIAccessPermission(SecurityPermission):
    """Special permission for PII data access."""
    
    def has_permission(self, request: Request, view: APIView) -> bool:
        if not super().has_permission(request, view):
            return False
        
        # Only super admin can access raw PII
        if request.user.role != 'SUPER_ADMIN':
            return False
        
        # Log PII access
        AuditLog.objects.create(
            user=request.user,
            action='PII_ACCESS',
            severity='HIGH',
            resource_type='pii_data',
            description=f'PII data access by {request.user.username}',
            ip_address=self.get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            success=True,
        )
        
        return True


# Decorators for function-based views
def require_permission(resource: str, action: str = 'read'):
    """Decorator to require specific permission."""
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request: HttpRequest, *args, **kwargs):
            if not request.user or not request.user.is_authenticated:
                raise PermissionDenied('Authentication required')
            
            if not RolePermissions.has_role_permission(request.user.role, resource, action):
                # Log unauthorized access
                AuditLog.objects.create(
                    user=request.user,
                    action='UNAUTHORIZED_ACCESS',
                    severity='HIGH',
                    resource_type=resource,
                    description=f'Unauthorized access attempt to {resource}:{action}',
                    ip_address=request.META.get('REMOTE_ADDR'),
                    user_agent=request.META.get('HTTP_USER_AGENT', ''),
                    success=False,
                )
                raise PermissionDenied(f'Permission denied for {resource}:{action}')
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def require_role(required_roles: List[str]):
    """Decorator to require specific roles."""
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request: HttpRequest, *args, **kwargs):
            if not request.user or not request.user.is_authenticated:
                raise PermissionDenied('Authentication required')
            
            if request.user.role not in required_roles:
                # Log unauthorized access
                AuditLog.objects.create(
                    user=request.user,
                    action='UNAUTHORIZED_ACCESS',
                    severity='HIGH',
                    description=f'Role {request.user.role} not in required roles {required_roles}',
                    ip_address=request.META.get('REMOTE_ADDR'),
                    user_agent=request.META.get('HTTP_USER_AGENT', ''),
                    success=False,
                )
                raise PermissionDenied(f'Role {request.user.role} not authorized')
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def require_branch_access(branch_field: str = 'branch_id'):
    """Decorator to require branch access for object."""
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request: HttpRequest, *args, **kwargs):
            if not request.user or not request.user.is_authenticated:
                raise PermissionDenied('Authentication required')
            
            # Get branch_id from URL parameters or request data
            branch_id = kwargs.get(branch_field) or request.GET.get(branch_field)
            
            if branch_id and not BranchAccessControl.has_branch_access(request.user, branch_id):
                AuditLog.objects.create(
                    user=request.user,
                    action='UNAUTHORIZED_ACCESS',
                    severity='HIGH',
                    description=f'Branch access denied for {branch_id}',
                    ip_address=request.META.get('REMOTE_ADDR'),
                    success=False,
                )
                raise PermissionDenied(f'Access denied for branch {branch_id}')
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


class PermissionChecker:
    """Utility class for checking permissions programmatically."""
    
    @staticmethod
    def check_user_permission(user: User, resource: str, action: str, branch_id: str = None) -> bool:
        """Check if user has permission with optional branch check."""
        # Check role permission
        if not RolePermissions.has_role_permission(user.role, resource, action):
            return False
        
        # Check branch access if specified
        if branch_id and not BranchAccessControl.has_branch_access(user, branch_id):
            return False
        
        return True
    
    @staticmethod
    def get_user_accessible_resources(user: User) -> Dict[str, List[str]]:
        """Get all resources accessible to user with their allowed actions."""
        accessible_resources = {}
        
        for resource, actions in RolePermissions.RESOURCE_PERMISSIONS.items():
            user_actions = []
            for action, allowed_roles in actions.items():
                if user.role in allowed_roles or '*' in allowed_roles:
                    user_actions.append(action)
            
            if user_actions:
                accessible_resources[resource] = user_actions
        
        return accessible_resources
    
    @staticmethod
    def can_user_manage_user(manager: User, target_user: User) -> bool:
        """Check if manager can manage target user."""
        # Super admin can manage anyone
        if manager.role == 'SUPER_ADMIN':
            return True
        
        # Security admin can manage non-admin users
        if manager.role == 'SECURITY_ADMIN':
            return target_user.role not in ['SUPER_ADMIN']
        
        # Manager can manage users in same branch with lower roles
        if manager.role == 'MANAGER':
            lower_roles = ['ANALYST', 'STAFF', 'VIEWER']
            same_branch = BranchAccessControl.has_branch_access(manager, target_user.branch_id)
            return target_user.role in lower_roles and same_branch
        
        return False
    
    @staticmethod
    def audit_permission_check(user: User, resource: str, action: str, success: bool, ip_address: str = None):
        """Audit permission check for compliance."""
        severity = 'MEDIUM' if success else 'HIGH'
        description = f'Permission check: {user.username} -> {resource}:{action} = {success}'
        
        AuditLog.objects.create(
            user=user,
            action='UNAUTHORIZED_ACCESS' if not success else 'DATA_ACCESS',
            severity=severity,
            resource_type=resource,
            description=description,
            ip_address=ip_address,
            success=success,
        )


class AttributeBasedAccessControl:
    """Attribute-Based Access Control (ABAC) for fine-grained permissions."""
    
    @staticmethod
    def evaluate_policy(user: User, resource: Any, action: str, context: Dict[str, Any] = None) -> bool:
        """
        Evaluate access policy based on user attributes, resource attributes, and context.
        
        This is a framework for implementing ABAC policies. Extend as needed.
        """
        context = context or {}
        
        # Time-based access control
        current_hour = timezone.now().hour
        if context.get('require_business_hours') and not (9 <= current_hour <= 17):
            return False
        
        # Location-based access control
        user_ip = context.get('ip_address')
        if context.get('require_office_ip') and user_ip:
            # Implement IP whitelist check
            office_ips = ['192.168.1.0/24', '10.0.0.0/8']  # Example
            # Add actual IP range checking logic
            pass
        
        # Data sensitivity-based control
        if hasattr(resource, 'sensitivity_level'):
            user_clearance = getattr(user, 'security_clearance', 'LOW')
            if resource.sensitivity_level == 'HIGH' and user_clearance != 'HIGH':
                return False
        
        # Dynamic role-based rules
        if hasattr(resource, 'owner_id'):
            # Users can access their own resources
            if str(resource.owner_id) == str(user.id):
                return True
        
        # Department-based access
        if hasattr(resource, 'department') and hasattr(user, 'department'):
            if resource.department != user.department and user.role not in ['SUPER_ADMIN', 'MANAGER']:
                return False
        
        return True
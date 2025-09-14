from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
from django.conf import settings
import logging
import re

logger = logging.getLogger(__name__)


class RoleBasedAccessMiddleware(MiddlewareMixin):
    """
    Middleware to enforce role-based access control across the application
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        super().__init__(get_response)
        
        # Define route patterns and required roles
        self.route_permissions = {
            # Authentication endpoints - accessible to all
            r'^/api/auth/(register|login)/?$': ['*'],
            r'^/api/auth/token/?$': ['*'],
            
            # Profile endpoints - authenticated users only
            r'^/api/auth/profile/?$': ['super_admin', 'manager', 'analyst', 'staff'],
            r'^/api/auth/password-change/?$': ['super_admin', 'manager', 'analyst', 'staff'],
            r'^/api/auth/logout/?$': ['super_admin', 'manager', 'analyst', 'staff'],
            r'^/api/auth/sessions/?$': ['super_admin', 'manager', 'analyst', 'staff'],
            
            # User management endpoints - super admin only
            r'^/api/auth/users/?$': ['super_admin'],
            r'^/api/auth/users/create/?$': ['super_admin'],
            
            # Dashboard endpoints - role specific
            r'^/api/dashboard/.*$': ['super_admin', 'manager', 'analyst'],
            
            # Reports endpoints - analysts and above
            r'^/api/reports/.*$': ['super_admin', 'manager', 'analyst'],
            
            # Branch-specific data - managers for their branch, super admins for all
            r'^/api/branches/[^/]+/.*$': ['super_admin', 'manager'],
            
            # Settings endpoints - super admin only
            r'^/api/settings/.*$': ['super_admin'],
            
            # Staff-specific endpoints - very limited
            r'^/api/staff/tasks/?$': ['staff'],
            r'^/api/staff/profile/?$': ['staff'],
        }
        
        # Compile regex patterns for better performance
        self.compiled_patterns = {
            re.compile(pattern): roles 
            for pattern, roles in self.route_permissions.items()
        }
    
    def process_request(self, request):
        """
        Process incoming request and check permissions
        """
        # Skip middleware for certain paths
        if self._should_skip_middleware(request):
            return None
        
        # Check if the route requires authentication
        required_roles = self._get_required_roles(request.path)
        
        if required_roles is None:
            # Route not defined in permissions, allow by default (will be handled by view permissions)
            return None
        
        if '*' in required_roles:
            # Route is accessible to all
            return None
        
        # Check if user is authenticated
        if not request.user or not request.user.is_authenticated:
            return JsonResponse({
                'error': 'Authentication required',
                'code': 'authentication_required'
            }, status=401)
        
        # Check if user has required role
        user_role = getattr(request.user, 'role', None)
        
        if user_role not in required_roles:
            logger.warning(
                f"Access denied for user {request.user.username} "
                f"(role: {user_role}) to {request.path}"
            )
            return JsonResponse({
                'error': 'Access denied. Insufficient permissions.',
                'code': 'access_denied',
                'required_roles': required_roles,
                'user_role': user_role
            }, status=403)
        
        # Additional branch-specific checks
        if user_role in ['manager', 'staff']:
            branch_access_denied = self._check_branch_access(request)
            if branch_access_denied:
                return branch_access_denied
        
        return None
    
    def _should_skip_middleware(self, request):
        """
        Check if middleware should be skipped for certain paths
        """
        skip_paths = [
            '/admin/',
            '/static/',
            '/media/',
            '/favicon.ico',
            '/api/docs/',
            '/api/schema/',
        ]
        
        return any(request.path.startswith(path) for path in skip_paths)
    
    def _get_required_roles(self, path):
        """
        Get required roles for a given path
        """
        for pattern, roles in self.compiled_patterns.items():
            if pattern.match(path):
                return roles
        return None
    
    def _check_branch_access(self, request):
        """
        Check if manager/staff can access branch-specific data
        """
        # Extract branch_id from URL
        path_parts = request.path.split('/')
        
        # Look for branch ID in URL pattern like /api/branches/{branch_id}/
        branch_id_from_url = None
        if 'branches' in path_parts:
            try:
                branches_index = path_parts.index('branches')
                if len(path_parts) > branches_index + 1:
                    branch_id_from_url = path_parts[branches_index + 1]
            except (ValueError, IndexError):
                pass
        
        # Check query parameters for branch_id
        branch_id_from_query = request.GET.get('branch_id')
        
        # Get the branch_id that's being accessed
        target_branch_id = branch_id_from_url or branch_id_from_query
        
        if target_branch_id and not request.user.can_access_branch(target_branch_id):
            logger.warning(
                f"Branch access denied for user {request.user.username} "
                f"to branch {target_branch_id}. User's branch: {request.user.branch_id}"
            )
            return JsonResponse({
                'error': 'Access denied to this branch data',
                'code': 'branch_access_denied',
                'accessible_branches': request.user.get_accessible_branches()
            }, status=403)
        
        return None
    
    def process_response(self, request, response):
        """
        Process the response (optional)
        """
        # Add security headers
        if hasattr(request, 'user') and request.user.is_authenticated:
            response['X-User-Role'] = getattr(request.user, 'role', 'unknown')
            if hasattr(request.user, 'branch_id') and request.user.branch_id:
                response['X-User-Branch'] = request.user.branch_id
        
        return response


class SecurityHeadersMiddleware(MiddlewareMixin):
    """
    Middleware to add security headers
    """
    
    def process_response(self, request, response):
        """
        Add security headers to response
        """
        # Add security headers
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        # Add API-specific headers
        if request.path.startswith('/api/'):
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
        
        return response


class RequestLoggingMiddleware(MiddlewareMixin):
    """
    Middleware to log API requests for audit purposes
    """
    
    def process_request(self, request):
        """
        Log incoming API requests
        """
        # Only log API requests
        if not request.path.startswith('/api/'):
            return None
        
        # Skip logging for certain endpoints
        skip_logging = [
            '/api/auth/token/',  # Too frequent
            '/api/health/',      # Health checks
        ]
        
        if any(request.path.startswith(path) for path in skip_logging):
            return None
        
        # Log request details
        user_info = 'anonymous'
        if hasattr(request, 'user') and request.user.is_authenticated:
            user_info = f"{request.user.username} ({request.user.role})"
        
        logger.info(
            f"API Request: {request.method} {request.path} - User: {user_info} - "
            f"IP: {self._get_client_ip(request)}"
        )
        
        return None
    
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
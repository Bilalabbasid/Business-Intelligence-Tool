"""
Security middleware for Django application providing CSP, HSTS, rate limiting,
authentication, and other security protections.
"""

import time
import json
import hashlib
import hmac
from typing import Dict, Any, Optional, Set, Callable
from django.conf import settings
from django.core.cache import cache
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.utils import timezone
from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth.models import AnonymousUser
from django.urls import resolve
from django.utils.crypto import constant_time_compare
import logging
from datetime import datetime, timedelta
import re
import ipaddress

from .audit import AuditContext, AuditEvent, AuditLogger
from .auth import JWTAuthenticator


logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(MiddlewareMixin):
    """Adds comprehensive security headers to HTTP responses."""
    
    def __init__(self, get_response):
        self.get_response = get_response
        
        # Security configuration from settings
        self.csp_policy = getattr(settings, 'CONTENT_SECURITY_POLICY', self._default_csp())
        self.hsts_max_age = getattr(settings, 'HSTS_MAX_AGE', 31536000)  # 1 year
        self.frame_options = getattr(settings, 'X_FRAME_OPTIONS', 'DENY')
        self.content_type_options = getattr(settings, 'X_CONTENT_TYPE_OPTIONS', 'nosniff')
        self.xss_protection = getattr(settings, 'X_XSS_PROTECTION', '1; mode=block')
        self.referrer_policy = getattr(settings, 'REFERRER_POLICY', 'strict-origin-when-cross-origin')
        
        super().__init__(get_response)
    
    def _default_csp(self) -> str:
        """Default Content Security Policy."""
        return (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https:; "
            "style-src 'self' 'unsafe-inline' https:; "
            "img-src 'self' data: https:; "
            "font-src 'self' https:; "
            "connect-src 'self' https: wss:; "
            "media-src 'self'; "
            "object-src 'none'; "
            "base-uri 'self'; "
            "form-action 'self'; "
            "frame-ancestors 'none'; "
            "upgrade-insecure-requests;"
        )
    
    def process_response(self, request: HttpRequest, response: HttpResponse) -> HttpResponse:
        """Add security headers to response."""
        
        # Content Security Policy
        if not response.get('Content-Security-Policy'):
            response['Content-Security-Policy'] = self.csp_policy
        
        # HTTP Strict Transport Security (HTTPS only)
        if request.is_secure() and not response.get('Strict-Transport-Security'):
            response['Strict-Transport-Security'] = f'max-age={self.hsts_max_age}; includeSubDomains; preload'
        
        # X-Frame-Options
        if not response.get('X-Frame-Options'):
            response['X-Frame-Options'] = self.frame_options
        
        # X-Content-Type-Options
        if not response.get('X-Content-Type-Options'):
            response['X-Content-Type-Options'] = self.content_type_options
        
        # X-XSS-Protection
        if not response.get('X-XSS-Protection'):
            response['X-XSS-Protection'] = self.xss_protection
        
        # Referrer Policy
        if not response.get('Referrer-Policy'):
            response['Referrer-Policy'] = self.referrer_policy
        
        # Permissions Policy (Feature Policy successor)
        if not response.get('Permissions-Policy'):
            response['Permissions-Policy'] = (
                "geolocation=(), microphone=(), camera=(), "
                "payment=(), usb=(), accelerometer=(), gyroscope=(), "
                "magnetometer=(), midi=()"
            )
        
        # Remove server information
        if response.get('Server'):
            del response['Server']
        
        return response


class RateLimitMiddleware(MiddlewareMixin):
    """Rate limiting middleware with configurable limits per endpoint/user/IP."""
    
    def __init__(self, get_response):
        self.get_response = get_response
        
        # Rate limit configuration
        self.enabled = getattr(settings, 'RATE_LIMITING_ENABLED', True)
        self.default_limits = getattr(settings, 'RATE_LIMIT_DEFAULTS', {
            'anonymous': {'requests': 100, 'window': 3600},  # 100 req/hour for anonymous
            'authenticated': {'requests': 1000, 'window': 3600},  # 1000 req/hour for authenticated
        })
        
        # Endpoint-specific limits
        self.endpoint_limits = getattr(settings, 'RATE_LIMIT_ENDPOINTS', {
            'login': {'requests': 10, 'window': 600},  # 10 login attempts per 10 minutes
            'api': {'requests': 500, 'window': 3600},  # 500 API calls per hour
            'download': {'requests': 50, 'window': 3600},  # 50 downloads per hour
        })
        
        # Exempted IPs (internal systems, load balancers, etc.)
        self.exempt_ips = set(getattr(settings, 'RATE_LIMIT_EXEMPT_IPS', []))
        
        super().__init__(get_response)
    
    def process_request(self, request: HttpRequest) -> Optional[HttpResponse]:
        """Check rate limits before processing request."""
        
        if not self.enabled:
            return None
        
        # Get client IP
        client_ip = self._get_client_ip(request)
        
        # Check if IP is exempt
        if self._is_exempt_ip(client_ip):
            return None
        
        # Check rate limits
        if self._is_rate_limited(request, client_ip):
            return self._rate_limit_response(request, client_ip)
        
        return None
    
    def _get_client_ip(self, request: HttpRequest) -> str:
        """Get client IP address."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', '')
        return ip
    
    def _is_exempt_ip(self, ip: str) -> bool:
        """Check if IP is exempt from rate limiting."""
        if not ip or ip in self.exempt_ips:
            return True
        
        # Check if IP is in exempt networks
        try:
            ip_obj = ipaddress.ip_address(ip)
            for exempt_ip in self.exempt_ips:
                try:
                    if ip_obj in ipaddress.ip_network(exempt_ip, strict=False):
                        return True
                except ValueError:
                    continue
        except ValueError:
            pass
        
        return False
    
    def _is_rate_limited(self, request: HttpRequest, client_ip: str) -> bool:
        """Check if request should be rate limited."""
        
        # Get applicable limits
        limits = self._get_limits(request)
        
        # Create cache keys for different limit types
        keys = [
            f"rate_limit:ip:{client_ip}",
        ]
        
        if hasattr(request, 'user') and request.user.is_authenticated:
            keys.append(f"rate_limit:user:{request.user.id}")
        
        # Check endpoint-specific limits
        endpoint = self._get_endpoint_key(request)
        if endpoint:
            keys.append(f"rate_limit:endpoint:{endpoint}:{client_ip}")
        
        # Check each limit
        for key in keys:
            limit_config = self._get_limit_config(key, limits, endpoint)
            if self._check_limit(key, limit_config):
                return True
        
        return False
    
    def _get_limits(self, request: HttpRequest) -> Dict[str, Any]:
        """Get applicable rate limits for request."""
        if hasattr(request, 'user') and request.user.is_authenticated:
            return self.default_limits['authenticated']
        else:
            return self.default_limits['anonymous']
    
    def _get_endpoint_key(self, request: HttpRequest) -> Optional[str]:
        """Get endpoint key for specific rate limiting."""
        try:
            resolved = resolve(request.path)
            view_name = resolved.view_name
            
            # Map view names to endpoint keys
            if 'login' in view_name.lower():
                return 'login'
            elif 'api' in view_name.lower():
                return 'api'
            elif 'download' in view_name.lower():
                return 'download'
            
        except Exception:
            pass
        
        return None
    
    def _get_limit_config(self, key: str, default_limits: Dict[str, Any], 
                         endpoint: str = None) -> Dict[str, Any]:
        """Get limit configuration for specific key."""
        if endpoint and endpoint in self.endpoint_limits:
            return self.endpoint_limits[endpoint]
        return default_limits
    
    def _check_limit(self, key: str, limit_config: Dict[str, Any]) -> bool:
        """Check if specific limit is exceeded."""
        current_count = cache.get(key, 0)
        
        if current_count >= limit_config['requests']:
            return True
        
        # Increment counter
        try:
            cache.set(key, current_count + 1, limit_config['window'])
        except Exception as e:
            logger.error(f"Rate limit cache error: {e}")
        
        return False
    
    def _rate_limit_response(self, request: HttpRequest, client_ip: str) -> HttpResponse:
        """Return rate limit exceeded response."""
        
        # Log rate limit violation
        AuditLogger.log_event(AuditEvent(
            action='RATE_LIMIT_EXCEEDED',
            severity='MEDIUM',
            resource_type='rate_limit',
            description=f'Rate limit exceeded for IP {client_ip}',
            success=False,
            ip_address=client_ip,
            user_id=request.user.id if hasattr(request, 'user') and request.user.is_authenticated else None,
            metadata={
                'path': request.path,
                'method': request.method,
                'user_agent': request.META.get('HTTP_USER_AGENT', ''),
            }
        ))
        
        return JsonResponse({
            'error': 'Rate limit exceeded',
            'message': 'Too many requests. Please try again later.',
            'code': 'RATE_LIMIT_EXCEEDED'
        }, status=429)


class JWTAuthenticationMiddleware(MiddlewareMixin):
    """JWT authentication middleware for API requests."""
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.jwt_auth = JWTAuthenticator()
        
        # Paths that don't require authentication
        self.exempt_paths = getattr(settings, 'JWT_EXEMPT_PATHS', [
            '/health/',
            '/docs/',
            '/auth/login/',
            '/auth/register/',
        ])
        
        super().__init__(get_response)
    
    def process_request(self, request: HttpRequest) -> Optional[HttpResponse]:
        """Authenticate JWT tokens in requests."""
        
        # Skip authentication for exempt paths
        if self._is_exempt_path(request.path):
            return None
        
        # Get JWT token from header
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        if not auth_header.startswith('Bearer '):
            # For API endpoints, require authentication
            if request.path.startswith('/api/'):
                return JsonResponse({
                    'error': 'Authentication required',
                    'message': 'Missing or invalid authorization header',
                    'code': 'AUTH_REQUIRED'
                }, status=401)
            return None
        
        token = auth_header.split(' ')[1]
        
        try:
            # Validate and decode JWT
            payload = self.jwt_auth.decode_jwt(token)
            
            # Get user from payload
            from django.contrib.auth.models import User
            user = User.objects.get(id=payload['user_id'])
            
            # Set user on request
            request.user = user
            request.jwt_payload = payload
            
            # Update last activity
            self._update_user_activity(user, request)
            
        except Exception as e:
            # Log authentication failure
            AuditLogger.log_event(AuditEvent(
                action='JWT_AUTH_FAILED',
                severity='MEDIUM',
                resource_type='authentication',
                description=f'JWT authentication failed: {str(e)}',
                success=False,
                ip_address=self._get_client_ip(request),
                metadata={'error': str(e), 'path': request.path}
            ))
            
            return JsonResponse({
                'error': 'Authentication failed',
                'message': 'Invalid or expired token',
                'code': 'AUTH_FAILED'
            }, status=401)
        
        return None
    
    def _is_exempt_path(self, path: str) -> bool:
        """Check if path is exempt from JWT authentication."""
        for exempt_path in self.exempt_paths:
            if path.startswith(exempt_path):
                return True
        return False
    
    def _get_client_ip(self, request: HttpRequest) -> str:
        """Get client IP address."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', '')
        return ip
    
    def _update_user_activity(self, user, request: HttpRequest):
        """Update user's last activity timestamp."""
        cache_key = f"user_activity:{user.id}"
        cache.set(cache_key, timezone.now(), 3600)  # Cache for 1 hour


class AuditMiddleware(MiddlewareMixin):
    """Audit middleware to automatically log request/response activity."""
    
    def __init__(self, get_response):
        self.get_response = get_response
        
        # Configuration
        self.enabled = getattr(settings, 'AUDIT_MIDDLEWARE_ENABLED', True)
        self.log_requests = getattr(settings, 'AUDIT_LOG_REQUESTS', True)
        self.log_responses = getattr(settings, 'AUDIT_LOG_RESPONSES', False)
        self.sensitive_fields = getattr(settings, 'AUDIT_SENSITIVE_FIELDS', [
            'password', 'token', 'secret', 'key', 'authorization'
        ])
        
        # Paths to exclude from audit logging
        self.exclude_paths = getattr(settings, 'AUDIT_EXCLUDE_PATHS', [
            '/health/',
            '/metrics/',
            '/static/',
            '/media/',
        ])
        
        super().__init__(get_response)
    
    def process_request(self, request: HttpRequest) -> Optional[HttpResponse]:
        """Start audit context for request."""
        
        if not self.enabled or self._should_exclude_path(request.path):
            return None
        
        # Create audit context
        correlation_id = self._generate_correlation_id(request)
        audit_context = AuditContext(correlation_id=correlation_id, request=request)
        
        # Store context in request for later use
        request.audit_context = audit_context
        request.audit_start_time = time.time()
        
        # Enter the context
        audit_context.__enter__()
        
        # Log request if enabled
        if self.log_requests:
            self._log_request(request, audit_context)
        
        return None
    
    def process_response(self, request: HttpRequest, response: HttpResponse) -> HttpResponse:
        """End audit context and log response."""
        
        if not self.enabled or not hasattr(request, 'audit_context'):
            return response
        
        try:
            # Calculate request duration
            duration = time.time() - getattr(request, 'audit_start_time', time.time())
            
            # Log response if enabled
            if self.log_responses:
                self._log_response(request, response, request.audit_context, duration)
            
            # Exit audit context
            request.audit_context.__exit__(None, None, None)
            
        except Exception as e:
            logger.error(f"Audit middleware error: {e}")
        
        return response
    
    def process_exception(self, request: HttpRequest, exception: Exception) -> None:
        """Handle exceptions in audit context."""
        
        if hasattr(request, 'audit_context'):
            try:
                # Log the exception
                request.audit_context.add_event(AuditEvent(
                    action='REQUEST_EXCEPTION',
                    severity='HIGH',
                    resource_type='request',
                    description=f'Request exception: {str(exception)}',
                    success=False,
                    metadata={
                        'exception_type': type(exception).__name__,
                        'exception_message': str(exception),
                        'path': request.path,
                        'method': request.method,
                    }
                ))
                
                # Exit context with exception
                request.audit_context.__exit__(type(exception), exception, None)
                
            except Exception as e:
                logger.error(f"Audit exception handling error: {e}")
        
        return None
    
    def _should_exclude_path(self, path: str) -> bool:
        """Check if path should be excluded from auditing."""
        return any(path.startswith(exclude) for exclude in self.exclude_paths)
    
    def _generate_correlation_id(self, request: HttpRequest) -> str:
        """Generate correlation ID for request."""
        # Use existing correlation ID from headers if present
        correlation_id = request.META.get('HTTP_X_CORRELATION_ID')
        if correlation_id:
            return correlation_id
        
        # Generate new correlation ID
        import uuid
        return str(uuid.uuid4())
    
    def _log_request(self, request: HttpRequest, audit_context: AuditContext):
        """Log incoming request."""
        
        # Prepare request data
        request_data = {
            'method': request.method,
            'path': request.path,
            'query_params': dict(request.GET) if request.GET else {},
            'headers': self._sanitize_headers(dict(request.META)),
            'content_type': request.content_type,
            'user_agent': request.META.get('HTTP_USER_AGENT', ''),
        }
        
        # Add body data for POST/PUT requests (sanitized)
        if request.method in ['POST', 'PUT', 'PATCH'] and hasattr(request, 'body'):
            try:
                if request.content_type == 'application/json':
                    body_data = json.loads(request.body.decode('utf-8'))
                    request_data['body'] = self._sanitize_data(body_data)
                else:
                    request_data['body_size'] = len(request.body)
            except Exception:
                request_data['body_size'] = len(request.body) if request.body else 0
        
        audit_context.add_event(AuditEvent(
            action='REQUEST_RECEIVED',
            severity='LOW',
            resource_type='request',
            description=f'{request.method} {request.path}',
            success=True,
            metadata=request_data
        ))
    
    def _log_response(self, request: HttpRequest, response: HttpResponse, 
                     audit_context: AuditContext, duration: float):
        """Log response."""
        
        response_data = {
            'status_code': response.status_code,
            'content_type': response.get('Content-Type', ''),
            'duration_ms': round(duration * 1000, 2),
            'content_length': len(response.content) if hasattr(response, 'content') else 0,
        }
        
        # Determine success based on status code
        success = 200 <= response.status_code < 400
        severity = 'LOW' if success else ('MEDIUM' if response.status_code < 500 else 'HIGH')
        
        audit_context.add_event(AuditEvent(
            action='REQUEST_COMPLETED',
            severity=severity,
            resource_type='request',
            description=f'{request.method} {request.path} -> {response.status_code}',
            success=success,
            metadata=response_data
        ))
    
    def _sanitize_headers(self, headers: Dict[str, str]) -> Dict[str, str]:
        """Sanitize headers to remove sensitive information."""
        sanitized = {}
        
        for key, value in headers.items():
            if any(sensitive in key.lower() for sensitive in self.sensitive_fields):
                sanitized[key] = '[REDACTED]'
            else:
                sanitized[key] = str(value)[:200]  # Truncate long values
        
        return sanitized
    
    def _sanitize_data(self, data: Any) -> Any:
        """Recursively sanitize data to remove sensitive fields."""
        if isinstance(data, dict):
            sanitized = {}
            for key, value in data.items():
                if any(sensitive in key.lower() for sensitive in self.sensitive_fields):
                    sanitized[key] = '[REDACTED]'
                else:
                    sanitized[key] = self._sanitize_data(value)
            return sanitized
        
        elif isinstance(data, list):
            return [self._sanitize_data(item) for item in data[:10]]  # Limit list size
        
        elif isinstance(data, str):
            return data[:500]  # Truncate long strings
        
        else:
            return data


class CSRFSecurityMiddleware(MiddlewareMixin):
    """Enhanced CSRF protection with additional security features."""
    
    def __init__(self, get_response):
        self.get_response = get_response
        
        # Configuration
        self.enabled = getattr(settings, 'ENHANCED_CSRF_ENABLED', True)
        self.require_referer = getattr(settings, 'CSRF_REQUIRE_REFERER', True)
        self.allowed_origins = getattr(settings, 'CSRF_ALLOWED_ORIGINS', [])
        
        super().__init__(get_response)
    
    def process_request(self, request: HttpRequest) -> Optional[HttpResponse]:
        """Enhanced CSRF validation."""
        
        if not self.enabled or request.method in ['GET', 'HEAD', 'OPTIONS', 'TRACE']:
            return None
        
        # Check for API requests (use different validation)
        if request.path.startswith('/api/'):
            return self._validate_api_request(request)
        
        # Standard web form validation
        return self._validate_web_request(request)
    
    def _validate_api_request(self, request: HttpRequest) -> Optional[HttpResponse]:
        """Validate API requests."""
        
        # For API requests, we rely on JWT authentication
        # Additional validation can be added here
        
        return None
    
    def _validate_web_request(self, request: HttpRequest) -> Optional[HttpResponse]:
        """Validate web form requests."""
        
        if self.require_referer:
            referer = request.META.get('HTTP_REFERER')
            if not referer or not self._is_valid_referer(request, referer):
                
                # Log CSRF violation
                AuditLogger.log_event(AuditEvent(
                    action='CSRF_VIOLATION',
                    severity='HIGH',
                    resource_type='csrf',
                    description='CSRF validation failed: invalid referer',
                    success=False,
                    ip_address=self._get_client_ip(request),
                    metadata={
                        'referer': referer,
                        'path': request.path,
                        'method': request.method,
                    }
                ))
                
                return JsonResponse({
                    'error': 'CSRF validation failed',
                    'message': 'Request blocked for security reasons',
                    'code': 'CSRF_FAILED'
                }, status=403)
        
        return None
    
    def _is_valid_referer(self, request: HttpRequest, referer: str) -> bool:
        """Check if referer is valid."""
        from urllib.parse import urlparse
        
        try:
            parsed_referer = urlparse(referer)
            request_host = request.get_host()
            
            # Check if referer matches request host
            if parsed_referer.netloc == request_host:
                return True
            
            # Check allowed origins
            if parsed_referer.netloc in self.allowed_origins:
                return True
            
        except Exception:
            pass
        
        return False
    
    def _get_client_ip(self, request: HttpRequest) -> str:
        """Get client IP address."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', '')
        return ip


class SecurityMonitoringMiddleware(MiddlewareMixin):
    """Middleware for security monitoring and threat detection."""
    
    def __init__(self, get_response):
        self.get_response = get_response
        
        # Suspicious patterns
        self.suspicious_patterns = [
            r'(?i)(union\s+select|script\s*>|javascript:|vbscript:)',  # SQL injection, XSS
            r'(?i)(\.\.\/|\.\.\\)',  # Path traversal
            r'(?i)(<script|<iframe|<object)',  # HTML injection
            r'(?i)(eval\s*\(|expression\s*\()',  # Code injection
        ]
        
        # Compiled patterns for performance
        self.compiled_patterns = [re.compile(pattern) for pattern in self.suspicious_patterns]
        
        super().__init__(get_response)
    
    def process_request(self, request: HttpRequest) -> Optional[HttpResponse]:
        """Monitor request for suspicious activity."""
        
        # Check for suspicious patterns in URL and parameters
        suspicious_found = []
        
        # Check URL path
        if self._contains_suspicious_content(request.path):
            suspicious_found.append('path')
        
        # Check query parameters
        for key, value in request.GET.items():
            if self._contains_suspicious_content(f"{key}={value}"):
                suspicious_found.append(f'query_param:{key}')
        
        # Check POST data
        if request.method == 'POST' and hasattr(request, 'POST'):
            for key, value in request.POST.items():
                if self._contains_suspicious_content(f"{key}={value}"):
                    suspicious_found.append(f'post_param:{key}')
        
        # Log suspicious activity
        if suspicious_found:
            AuditLogger.log_event(AuditEvent(
                action='SUSPICIOUS_REQUEST',
                severity='HIGH',
                resource_type='security',
                description=f'Suspicious patterns detected: {", ".join(suspicious_found)}',
                success=False,
                ip_address=self._get_client_ip(request),
                user_id=request.user.id if hasattr(request, 'user') and request.user.is_authenticated else None,
                metadata={
                    'patterns': suspicious_found,
                    'path': request.path,
                    'method': request.method,
                    'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                }
            ))
            
            # Optionally block the request
            block_request = getattr(settings, 'BLOCK_SUSPICIOUS_REQUESTS', False)
            if block_request:
                return JsonResponse({
                    'error': 'Request blocked',
                    'message': 'Suspicious activity detected',
                    'code': 'SECURITY_VIOLATION'
                }, status=400)
        
        return None
    
    def _contains_suspicious_content(self, content: str) -> bool:
        """Check if content contains suspicious patterns."""
        return any(pattern.search(content) for pattern in self.compiled_patterns)
    
    def _get_client_ip(self, request: HttpRequest) -> str:
        """Get client IP address."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', '')
        return ip
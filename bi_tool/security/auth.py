"""
Authentication utilities including JWT, OIDC/SAML, MFA, and secure password handling.
"""

import jwt
import pyotp
import secrets
import hashlib
import hmac
import time
from datetime import datetime, timedelta
from typing import Dict, Optional, Any, Tuple
from urllib.parse import urlencode
import requests

from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.hashers import make_password, check_password
from django.core.cache import cache
from django.utils import timezone
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import os

from .models import User, SessionToken, AuditLog


class SecuritySettings:
    """Security configuration constants."""
    
    # JWT Settings
    JWT_SECRET_KEY = getattr(settings, 'JWT_SECRET_KEY', settings.SECRET_KEY)
    JWT_ACCESS_TOKEN_LIFETIME = getattr(settings, 'JWT_ACCESS_TOKEN_LIFETIME', 900)  # 15 minutes
    JWT_REFRESH_TOKEN_LIFETIME = getattr(settings, 'JWT_REFRESH_TOKEN_LIFETIME', 86400 * 7)  # 7 days
    JWT_ALGORITHM = getattr(settings, 'JWT_ALGORITHM', 'HS256')
    
    # Password Policy
    PASSWORD_MIN_LENGTH = getattr(settings, 'PASSWORD_MIN_LENGTH', 10)
    PASSWORD_REQUIRE_UPPERCASE = getattr(settings, 'PASSWORD_REQUIRE_UPPERCASE', True)
    PASSWORD_REQUIRE_LOWERCASE = getattr(settings, 'PASSWORD_REQUIRE_LOWERCASE', True)
    PASSWORD_REQUIRE_DIGITS = getattr(settings, 'PASSWORD_REQUIRE_DIGITS', True)
    PASSWORD_REQUIRE_SYMBOLS = getattr(settings, 'PASSWORD_REQUIRE_SYMBOLS', True)
    PASSWORD_HISTORY_COUNT = getattr(settings, 'PASSWORD_HISTORY_COUNT', 5)
    PASSWORD_EXPIRE_DAYS = getattr(settings, 'PASSWORD_EXPIRE_DAYS', 90)
    
    # Account Lockout
    MAX_LOGIN_ATTEMPTS = getattr(settings, 'MAX_LOGIN_ATTEMPTS', 5)
    LOCKOUT_DURATION_MINUTES = getattr(settings, 'LOCKOUT_DURATION_MINUTES', 30)
    
    # MFA Settings
    MFA_ISSUER_NAME = getattr(settings, 'MFA_ISSUER_NAME', 'BI Tool')
    MFA_BACKUP_CODES_COUNT = getattr(settings, 'MFA_BACKUP_CODES_COUNT', 10)
    
    # SSO Settings
    OIDC_CLIENT_ID = getattr(settings, 'OIDC_CLIENT_ID', '')
    OIDC_CLIENT_SECRET = getattr(settings, 'OIDC_CLIENT_SECRET', '')
    OIDC_DISCOVERY_URL = getattr(settings, 'OIDC_DISCOVERY_URL', '')
    SAML_SETTINGS = getattr(settings, 'SAML_SETTINGS', {})


class PasswordValidator:
    """Enhanced password validation with security policies."""
    
    @staticmethod
    def validate_password(password: str, user: Optional[User] = None) -> Tuple[bool, list]:
        """
        Validate password against security policy.
        
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        # Length check
        if len(password) < SecuritySettings.PASSWORD_MIN_LENGTH:
            errors.append(f'Password must be at least {SecuritySettings.PASSWORD_MIN_LENGTH} characters long')
        
        # Complexity checks
        if SecuritySettings.PASSWORD_REQUIRE_UPPERCASE and not any(c.isupper() for c in password):
            errors.append('Password must contain at least one uppercase letter')
        
        if SecuritySettings.PASSWORD_REQUIRE_LOWERCASE and not any(c.islower() for c in password):
            errors.append('Password must contain at least one lowercase letter')
        
        if SecuritySettings.PASSWORD_REQUIRE_DIGITS and not any(c.isdigit() for c in password):
            errors.append('Password must contain at least one digit')
        
        if SecuritySettings.PASSWORD_REQUIRE_SYMBOLS and not any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in password):
            errors.append('Password must contain at least one special character')
        
        # User-specific checks
        if user:
            # Check against username
            if user.username.lower() in password.lower():
                errors.append('Password cannot contain username')
            
            # Check against email
            if user.email and user.email.split('@')[0].lower() in password.lower():
                errors.append('Password cannot contain email address')
        
        # Common passwords check (basic implementation)
        if PasswordValidator.is_common_password(password):
            errors.append('Password is too common')
        
        return len(errors) == 0, errors
    
    @staticmethod
    def is_common_password(password: str) -> bool:
        """Check against common passwords list."""
        common_passwords = [
            'password', '123456', '123456789', '12345678', '12345',
            'qwerty', 'abc123', 'password123', 'admin', 'letmein',
            'welcome', 'monkey', '1234567890', 'password1'
        ]
        return password.lower() in common_passwords
    
    @staticmethod
    def check_password_breach(password: str) -> bool:
        """
        Check password against HaveIBeenPwned API (optional feature).
        
        Returns True if password has been breached.
        """
        try:
            # Hash password with SHA-1
            sha1_hash = hashlib.sha1(password.encode()).hexdigest().upper()
            hash_prefix = sha1_hash[:5]
            hash_suffix = sha1_hash[5:]
            
            # Query HaveIBeenPwned API
            url = f'https://api.pwnedpasswords.com/range/{hash_prefix}'
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                hashes = response.text.split('\n')
                for hash_line in hashes:
                    if hash_line.startswith(hash_suffix):
                        return True
            
            return False
        except Exception:
            # If API is unavailable, don't block password change
            return False


class JWTAuthenticator:
    """JWT token management and authentication."""
    
    @staticmethod
    def generate_tokens(user: User, ip_address: str = None, user_agent: str = None) -> Dict[str, str]:
        """Generate access and refresh tokens for user."""
        now = timezone.now()
        
        # Generate access token
        access_payload = {
            'user_id': str(user.id),
            'username': user.username,
            'role': user.role,
            'branch_id': user.branch_id,
            'allowed_branches': user.allowed_branches,
            'resource_scopes': user.resource_scopes,
            'iat': int(now.timestamp()),
            'exp': int((now + timedelta(seconds=SecuritySettings.JWT_ACCESS_TOKEN_LIFETIME)).timestamp()),
            'token_type': 'access',
        }
        
        access_token = jwt.encode(
            access_payload,
            SecuritySettings.JWT_SECRET_KEY,
            algorithm=SecuritySettings.JWT_ALGORITHM
        )
        
        # Generate refresh token
        refresh_token = secrets.token_urlsafe(32)
        
        # Store tokens in database
        SessionToken.create_token(
            user=user,
            token_type='ACCESS',
            raw_token=access_token,
            expires_in_seconds=SecuritySettings.JWT_ACCESS_TOKEN_LIFETIME,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        
        SessionToken.create_token(
            user=user,
            token_type='REFRESH',
            raw_token=refresh_token,
            expires_in_seconds=SecuritySettings.JWT_REFRESH_TOKEN_LIFETIME,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        
        return {
            'access_token': access_token,
            'refresh_token': refresh_token,
            'token_type': 'Bearer',
            'expires_in': SecuritySettings.JWT_ACCESS_TOKEN_LIFETIME,
        }
    
    @staticmethod
    def verify_token(token: str) -> Optional[Dict[str, Any]]:
        """Verify and decode JWT token."""
        try:
            payload = jwt.decode(
                token,
                SecuritySettings.JWT_SECRET_KEY,
                algorithms=[SecuritySettings.JWT_ALGORITHM]
            )
            
            # Check if token is in database and valid
            session = SessionToken.verify_token(token, 'ACCESS')
            if not session:
                return None
            
            # Update last used timestamp
            session.update_last_used()
            
            return payload
            
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
    
    @staticmethod
    def refresh_token(refresh_token: str, ip_address: str = None) -> Optional[Dict[str, str]]:
        """Refresh access token using refresh token."""
        session = SessionToken.verify_token(refresh_token, 'REFRESH')
        if not session:
            return None
        
        # Generate new tokens
        new_tokens = JWTAuthenticator.generate_tokens(
            user=session.user,
            ip_address=ip_address,
            user_agent=session.user_agent,
        )
        
        # Revoke old refresh token
        session.revoke('Token refreshed')
        
        return new_tokens
    
    @staticmethod
    def revoke_token(token: str, token_type: str = 'ACCESS'):
        """Revoke a token."""
        session = SessionToken.verify_token(token, token_type)
        if session:
            session.revoke('Manual revocation')
            return True
        return False
    
    @staticmethod
    def revoke_all_user_tokens(user: User):
        """Revoke all tokens for a user."""
        SessionToken.objects.filter(user=user, is_revoked=False).update(
            is_revoked=True,
            revoked_at=timezone.now(),
            revocation_reason='All tokens revoked'
        )


class MFAManager:
    """Multi-Factor Authentication management."""
    
    @staticmethod
    def generate_secret() -> str:
        """Generate new MFA secret."""
        return pyotp.random_base32()
    
    @staticmethod
    def get_provisioning_uri(user: User, secret: str) -> str:
        """Get QR code provisioning URI."""
        totp = pyotp.TOTP(secret)
        return totp.provisioning_uri(
            name=user.username,
            issuer_name=SecuritySettings.MFA_ISSUER_NAME
        )
    
    @staticmethod
    def verify_totp(secret: str, token: str) -> bool:
        """Verify TOTP token."""
        totp = pyotp.TOTP(secret)
        return totp.verify(token, valid_window=1)  # Allow 1 window tolerance
    
    @staticmethod
    def enable_mfa(user: User, totp_token: str) -> Tuple[bool, Optional[str]]:
        """Enable MFA for user after verifying initial token."""
        if not user.mfa_secret:
            user.mfa_secret = MFAManager.generate_secret()
            user.save(update_fields=['mfa_secret'])
        
        if MFAManager.verify_totp(user.mfa_secret, totp_token):
            user.mfa_enabled = True
            user.save(update_fields=['mfa_enabled'])
            
            # Log MFA enabled
            AuditLog.objects.create(
                user=user,
                action='MFA_ENABLED',
                severity='MEDIUM',
                resource_type='user',
                resource_id=str(user.id),
                description=f'MFA enabled for user {user.username}',
                success=True,
            )
            
            return True, None
        else:
            return False, 'Invalid TOTP token'
    
    @staticmethod
    def disable_mfa(user: User, password: str, totp_token: str = None) -> Tuple[bool, Optional[str]]:
        """Disable MFA for user with password and optional TOTP verification."""
        if not check_password(password, user.password):
            return False, 'Invalid password'
        
        if user.mfa_enabled and totp_token:
            if not MFAManager.verify_totp(user.mfa_secret, totp_token):
                return False, 'Invalid TOTP token'
        
        user.mfa_enabled = False
        user.mfa_secret = ''
        user.save(update_fields=['mfa_enabled', 'mfa_secret'])
        
        # Revoke all tokens to force re-authentication
        JWTAuthenticator.revoke_all_user_tokens(user)
        
        # Log MFA disabled
        AuditLog.objects.create(
            user=user,
            action='MFA_DISABLED',
            severity='HIGH',
            resource_type='user',
            resource_id=str(user.id),
            description=f'MFA disabled for user {user.username}',
            success=True,
        )
        
        return True, None
    
    @staticmethod
    def generate_backup_codes(user: User) -> list:
        """Generate MFA backup codes."""
        codes = []
        for _ in range(SecuritySettings.MFA_BACKUP_CODES_COUNT):
            code = secrets.token_hex(4).upper()
            codes.append(code)
        
        # Store hashed backup codes
        hashed_codes = [hashlib.sha256(code.encode()).hexdigest() for code in codes]
        cache.set(f'mfa_backup_codes_{user.id}', hashed_codes, timeout=86400 * 30)  # 30 days
        
        return codes
    
    @staticmethod
    def verify_backup_code(user: User, code: str) -> bool:
        """Verify and consume MFA backup code."""
        hashed_codes = cache.get(f'mfa_backup_codes_{user.id}', [])
        code_hash = hashlib.sha256(code.encode()).hexdigest()
        
        if code_hash in hashed_codes:
            hashed_codes.remove(code_hash)
            cache.set(f'mfa_backup_codes_{user.id}', hashed_codes, timeout=86400 * 30)
            
            # Log backup code usage
            AuditLog.objects.create(
                user=user,
                action='MFA_BACKUP_CODE_USED',
                severity='MEDIUM',
                resource_type='user',
                resource_id=str(user.id),
                description=f'MFA backup code used for user {user.username}',
                success=True,
            )
            
            return True
        return False


class OIDCAuthenticator:
    """OpenID Connect authentication provider."""
    
    def __init__(self):
        self.client_id = SecuritySettings.OIDC_CLIENT_ID
        self.client_secret = SecuritySettings.OIDC_CLIENT_SECRET
        self.discovery_url = SecuritySettings.OIDC_DISCOVERY_URL
        self._discovery_document = None
    
    def get_discovery_document(self):
        """Get OIDC discovery document."""
        if not self._discovery_document:
            try:
                response = requests.get(self.discovery_url, timeout=10)
                response.raise_for_status()
                self._discovery_document = response.json()
            except requests.RequestException:
                raise Exception('Failed to fetch OIDC discovery document')
        return self._discovery_document
    
    def get_authorization_url(self, redirect_uri: str, state: str = None) -> str:
        """Generate authorization URL for OIDC flow."""
        discovery = self.get_discovery_document()
        auth_endpoint = discovery['authorization_endpoint']
        
        params = {
            'client_id': self.client_id,
            'response_type': 'code',
            'scope': 'openid profile email',
            'redirect_uri': redirect_uri,
            'state': state or secrets.token_urlsafe(32),
        }
        
        return f"{auth_endpoint}?{urlencode(params)}"
    
    def exchange_code_for_tokens(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        """Exchange authorization code for tokens."""
        discovery = self.get_discovery_document()
        token_endpoint = discovery['token_endpoint']
        
        data = {
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': redirect_uri,
            'client_id': self.client_id,
            'client_secret': self.client_secret,
        }
        
        response = requests.post(token_endpoint, data=data, timeout=10)
        response.raise_for_status()
        return response.json()
    
    def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """Get user information from OIDC provider."""
        discovery = self.get_discovery_document()
        userinfo_endpoint = discovery['userinfo_endpoint']
        
        headers = {'Authorization': f'Bearer {access_token}'}
        response = requests.get(userinfo_endpoint, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json()
    
    def authenticate_user(self, code: str, redirect_uri: str) -> Optional[User]:
        """Authenticate user via OIDC."""
        try:
            # Exchange code for tokens
            tokens = self.exchange_code_for_tokens(code, redirect_uri)
            
            # Get user info
            user_info = self.get_user_info(tokens['access_token'])
            
            # Find or create user
            username = user_info.get('preferred_username') or user_info.get('email')
            email = user_info.get('email')
            
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': email,
                    'first_name': user_info.get('given_name', ''),
                    'last_name': user_info.get('family_name', ''),
                    'role': 'VIEWER',  # Default role for SSO users
                }
            )
            
            if created:
                # Log new SSO user creation
                AuditLog.objects.create(
                    user=user,
                    action='USER_CREATED',
                    severity='MEDIUM',
                    resource_type='user',
                    resource_id=str(user.id),
                    description=f'New user created via OIDC: {username}',
                    metadata={'provider': 'OIDC', 'user_info': user_info},
                    success=True,
                )
            
            return user
            
        except Exception as e:
            # Log failed OIDC authentication
            AuditLog.objects.create(
                action='LOGIN_FAILED',
                severity='MEDIUM',
                resource_type='authentication',
                description=f'OIDC authentication failed: {str(e)}',
                success=False,
            )
            return None


class AuthenticationService:
    """Main authentication service orchestrating all auth methods."""
    
    @staticmethod
    def authenticate(username: str, password: str, ip_address: str = None, user_agent: str = None) -> Tuple[Optional[User], Optional[str]]:
        """
        Authenticate user with username/password.
        
        Returns:
            Tuple of (user, error_message)
        """
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            # Log failed login attempt
            AuditLog.objects.create(
                action='LOGIN_FAILED',
                severity='MEDIUM',
                description=f'Login attempt with invalid username: {username}',
                ip_address=ip_address,
                user_agent=user_agent,
                success=False,
            )
            return None, 'Invalid username or password'
        
        # Check if account is locked
        if user.is_account_locked():
            AuditLog.objects.create(
                user=user,
                action='LOGIN_FAILED',
                severity='HIGH',
                resource_type='user',
                resource_id=str(user.id),
                description=f'Login attempt on locked account: {username}',
                ip_address=ip_address,
                user_agent=user_agent,
                success=False,
            )
            return None, 'Account is temporarily locked'
        
        # Verify password
        if not check_password(password, user.password):
            user.failed_login_attempts += 1
            
            # Lock account if max attempts reached
            if user.failed_login_attempts >= SecuritySettings.MAX_LOGIN_ATTEMPTS:
                user.lock_account(SecuritySettings.LOCKOUT_DURATION_MINUTES)
                
                AuditLog.objects.create(
                    user=user,
                    action='SECURITY_EVENT',
                    severity='HIGH',
                    resource_type='user',
                    resource_id=str(user.id),
                    description=f'Account locked due to {user.failed_login_attempts} failed login attempts',
                    ip_address=ip_address,
                    user_agent=user_agent,
                    success=False,
                )
            else:
                user.save(update_fields=['failed_login_attempts'])
                
                AuditLog.objects.create(
                    user=user,
                    action='LOGIN_FAILED',
                    severity='MEDIUM',
                    resource_type='user',
                    resource_id=str(user.id),
                    description=f'Failed login attempt {user.failed_login_attempts}/{SecuritySettings.MAX_LOGIN_ATTEMPTS}',
                    ip_address=ip_address,
                    user_agent=user_agent,
                    success=False,
                )
            
            return None, 'Invalid username or password'
        
        # Check if password has expired
        if user.password_expires_at and timezone.now() > user.password_expires_at:
            return None, 'Password has expired'
        
        # Reset failed login attempts on successful authentication
        user.failed_login_attempts = 0
        user.last_login = timezone.now()
        user.save(update_fields=['failed_login_attempts', 'last_login'])
        
        return user, None
    
    @staticmethod
    def login(user: User, ip_address: str = None, user_agent: str = None, mfa_token: str = None) -> Tuple[Optional[Dict[str, str]], Optional[str]]:
        """
        Complete login process including MFA verification.
        
        Returns:
            Tuple of (tokens_dict, error_message)
        """
        # Check MFA requirement
        if user.mfa_enabled and not mfa_token:
            return None, 'MFA token required'
        
        # Verify MFA token if provided
        if user.mfa_enabled and mfa_token:
            if not MFAManager.verify_totp(user.mfa_secret, mfa_token):
                # Try backup code
                if not MFAManager.verify_backup_code(user, mfa_token):
                    AuditLog.objects.create(
                        user=user,
                        action='LOGIN_FAILED',
                        severity='HIGH',
                        resource_type='user',
                        resource_id=str(user.id),
                        description=f'Invalid MFA token for user {user.username}',
                        ip_address=ip_address,
                        user_agent=user_agent,
                        success=False,
                    )
                    return None, 'Invalid MFA token'
        
        # Generate tokens
        tokens = JWTAuthenticator.generate_tokens(user, ip_address, user_agent)
        
        # Log successful login
        AuditLog.objects.create(
            user=user,
            action='LOGIN',
            severity='LOW',
            resource_type='user',
            resource_id=str(user.id),
            description=f'Successful login for user {user.username}',
            ip_address=ip_address,
            user_agent=user_agent,
            success=True,
        )
        
        return tokens, None
    
    @staticmethod
    def logout(user: User, token: str, ip_address: str = None):
        """Logout user and revoke token."""
        JWTAuthenticator.revoke_token(token)
        
        # Log logout
        AuditLog.objects.create(
            user=user,
            action='LOGOUT',
            severity='LOW',
            resource_type='user',
            resource_id=str(user.id),
            description=f'User {user.username} logged out',
            ip_address=ip_address,
            success=True,
        )
    
    @staticmethod
    def change_password(user: User, old_password: str, new_password: str) -> Tuple[bool, Optional[str]]:
        """Change user password with validation."""
        # Verify old password
        if not check_password(old_password, user.password):
            AuditLog.objects.create(
                user=user,
                action='PASSWORD_CHANGE',
                severity='MEDIUM',
                resource_type='user',
                resource_id=str(user.id),
                description=f'Failed password change - invalid old password',
                success=False,
            )
            return False, 'Invalid current password'
        
        # Validate new password
        is_valid, errors = PasswordValidator.validate_password(new_password, user)
        if not is_valid:
            return False, '; '.join(errors)
        
        # Check password breach (optional)
        if PasswordValidator.check_password_breach(new_password):
            return False, 'Password has been found in data breaches'
        
        # Update password
        user.password = make_password(new_password)
        user.last_password_change = timezone.now()
        user.password_expires_at = timezone.now() + timedelta(days=SecuritySettings.PASSWORD_EXPIRE_DAYS)
        user.save(update_fields=['password', 'last_password_change', 'password_expires_at'])
        
        # Revoke all existing tokens to force re-authentication
        JWTAuthenticator.revoke_all_user_tokens(user)
        
        # Log password change
        AuditLog.objects.create(
            user=user,
            action='PASSWORD_CHANGE',
            severity='MEDIUM',
            resource_type='user',
            resource_id=str(user.id),
            description=f'Password changed for user {user.username}',
            success=True,
        )
        
        return True, None
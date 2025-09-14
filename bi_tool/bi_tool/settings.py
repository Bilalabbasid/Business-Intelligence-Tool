"""
Django settings for bi_tool project.
"""

from pathlib import Path
from decouple import config
from datetime import timedelta
import os

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config('SECRET_KEY', default='django-insecure-your-secret-key-here-change-in-production')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config('DEBUG', default=True, cast=bool)

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1', cast=lambda v: [s.strip() for s in v.split(',')])


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third-party apps
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    'django_celery_beat',
    'django_celery_results',
    
    # Local apps
    'core',
    'analytics',
    'api',
    'etl',
    'dq',
    'security',
    'pii',
]

MIDDLEWARE = [
    'security.middleware.SecurityHeadersMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'security.middleware.RateLimitMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'security.middleware.CSRFSecurityMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'security.middleware.JWTAuthenticationMiddleware',
    'core.middleware.RoleBasedAccessMiddleware',  # Custom RBAC middleware
    'security.middleware.AuditMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'security.middleware.SecurityMonitoringMiddleware',
]

ROOT_URLCONF = 'bi_tool.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'bi_tool.wsgi.application'


# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Custom User Model
AUTH_USER_MODEL = 'core.User'

# Password validation
# https://docs.djangoproject.com/en/4.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/4.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.2/howto/static-files/

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
# https://docs.djangoproject.com/en/4.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Django REST Framework settings
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}

# JWT Settings
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': False,

    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'VERIFYING_KEY': None,
    'AUDIENCE': None,
    'ISSUER': None,
    'JWK_URL': None,
    'LEEWAY': 0,

    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'USER_AUTHENTICATION_RULE': 'rest_framework_simplejwt.authentication.default_user_authentication_rule',

    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',
}

# CORS settings
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:8080",
    "http://127.0.0.1:8080",
]

CORS_ALLOW_CREDENTIALS = True

# Role-based access control settings
RBAC_ROLES = {
    'SUPER_ADMIN': 'super_admin',
    'MANAGER': 'manager', 
    'ANALYST': 'analyst',
    'STAFF': 'staff',
}

# Logging configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'django.log',
            'formatter': 'verbose',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
        'dq': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
        'etl': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# Celery Configuration
CELERY_BROKER_URL = config('REDIS_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND = config('REDIS_URL', default='redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
CELERY_ENABLE_UTC = True

# Celery Beat settings
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'

# Data Quality Configuration
DQ_RETENTION_DAYS = config('DQ_RETENTION_DAYS', default=90, cast=int)
DQ_DASHBOARD_URL = config('DQ_DASHBOARD_URL', default='http://localhost:3000/dq')

# Email configuration for DQ alerts
DQ_EMAIL_CONFIG = {
    'enabled': config('DQ_EMAIL_ENABLED', default=True, cast=bool),
    'smtp_host': config('SMTP_HOST', default='localhost'),
    'smtp_port': config('SMTP_PORT', default=587, cast=int),
    'use_tls': config('SMTP_USE_TLS', default=True, cast=bool),
    'username': config('SMTP_USERNAME', default=''),
    'password': config('SMTP_PASSWORD', default=''),
    'from_address': config('DQ_FROM_EMAIL', default='dq-alerts@company.com'),
    'admin_emails': config('DQ_ADMIN_EMAILS', default='', cast=lambda v: [s.strip() for s in v.split(',') if s.strip()]),
}

# Slack configuration for DQ alerts
DQ_SLACK_CONFIG = {
    'webhook_url': config('DQ_SLACK_WEBHOOK', default=''),
}

# PagerDuty configuration for DQ alerts
DQ_PAGERDUTY_CONFIG = {
    'integration_key': config('DQ_PAGERDUTY_KEY', default=''),
}

# Prometheus/monitoring configuration
PROMETHEUS_GATEWAY_URL = config('PROMETHEUS_GATEWAY_URL', default='')

# Data Warehouse Configuration
DATA_WAREHOUSE_CONFIG = {
    'postgresql': {
        'host': config('POSTGRES_HOST', default='localhost'),
        'port': config('POSTGRES_PORT', default=5432, cast=int),
        'database': config('POSTGRES_DB', default='bi_warehouse'),
        'username': config('POSTGRES_USER', default='postgres'),
        'password': config('POSTGRES_PASSWORD', default=''),
    },
    'clickhouse': {
        'host': config('CLICKHOUSE_HOST', default='localhost'),
        'port': config('CLICKHOUSE_PORT', default=9000, cast=int),
        'database': config('CLICKHOUSE_DB', default='bi_warehouse'),
        'username': config('CLICKHOUSE_USER', default='default'),
        'password': config('CLICKHOUSE_PASSWORD', default=''),
    }
}

# =============================================================================
# SECURITY, COMPLIANCE & DATA PRIVACY CONFIGURATION
# =============================================================================

# Security Headers Configuration
CONTENT_SECURITY_POLICY = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net https://unpkg.com; "
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdn.jsdelivr.net; "
    "font-src 'self' https://fonts.gstatic.com; "
    "img-src 'self' data: https:; "
    "connect-src 'self' https: wss: ws:; "
    "media-src 'self'; "
    "object-src 'none'; "
    "base-uri 'self'; "
    "form-action 'self'; "
    "frame-ancestors 'none'; "
    "upgrade-insecure-requests;"
)

HSTS_MAX_AGE = 31536000  # 1 year
X_FRAME_OPTIONS = 'DENY'
X_CONTENT_TYPE_OPTIONS = 'nosniff'
X_XSS_PROTECTION = '1; mode=block'
REFERRER_POLICY = 'strict-origin-when-cross-origin'

# Rate Limiting Configuration
RATE_LIMITING_ENABLED = config('RATE_LIMITING_ENABLED', default=True, cast=bool)
RATE_LIMIT_DEFAULTS = {
    'anonymous': {'requests': 100, 'window': 3600},  # 100 req/hour
    'authenticated': {'requests': 1000, 'window': 3600},  # 1000 req/hour
}
RATE_LIMIT_ENDPOINTS = {
    'login': {'requests': 10, 'window': 600},  # 10 login attempts per 10 minutes
    'api': {'requests': 500, 'window': 3600},  # 500 API calls per hour
    'download': {'requests': 50, 'window': 3600},  # 50 downloads per hour
}
RATE_LIMIT_EXEMPT_IPS = config('RATE_LIMIT_EXEMPT_IPS', default='127.0.0.1,::1', cast=lambda v: [s.strip() for s in v.split(',')])

# JWT Authentication Configuration
JWT_EXEMPT_PATHS = [
    '/health/',
    '/docs/',
    '/auth/login/',
    '/auth/register/',
    '/api/auth/login/',
    '/api/auth/register/',
    '/admin/',
]

# Audit Logging Configuration
AUDIT_MIDDLEWARE_ENABLED = config('AUDIT_MIDDLEWARE_ENABLED', default=True, cast=bool)
AUDIT_LOG_REQUESTS = config('AUDIT_LOG_REQUESTS', default=True, cast=bool)
AUDIT_LOG_RESPONSES = config('AUDIT_LOG_RESPONSES', default=False, cast=bool)
AUDIT_SENSITIVE_FIELDS = ['password', 'token', 'secret', 'key', 'authorization', 'ssn', 'credit_card']
AUDIT_EXCLUDE_PATHS = ['/health/', '/metrics/', '/static/', '/media/']

# SIEM Integration (Dummy configuration for development)
SIEM_ENABLED = config('SIEM_ENABLED', default=False, cast=bool)
SIEM_ENDPOINT = config('SIEM_ENDPOINT', default='https://dummy-siem.example.com/api/events')
SIEM_API_KEY = config('SIEM_API_KEY', default='dummy-siem-key-for-development')

# Key Management System Configuration
KMS_PROVIDER = config('KMS_PROVIDER', default='local')  # local, aws, vault
ENCRYPTION_MASTER_KEY = config('ENCRYPTION_MASTER_KEY', default=SECRET_KEY)
AUDIT_INTEGRITY_KEY = config('AUDIT_INTEGRITY_KEY', default=SECRET_KEY)

# AWS KMS Configuration (if using AWS KMS)
AWS_REGION = config('AWS_REGION', default='us-east-1')
AWS_ACCESS_KEY_ID = config('AWS_ACCESS_KEY_ID', default='')
AWS_SECRET_ACCESS_KEY = config('AWS_SECRET_ACCESS_KEY', default='')

# HashiCorp Vault Configuration (if using Vault)
VAULT_URL = config('VAULT_URL', default='http://localhost:8200')
VAULT_TOKEN = config('VAULT_TOKEN', default='')

# CSRF Security Configuration
ENHANCED_CSRF_ENABLED = config('ENHANCED_CSRF_ENABLED', default=True, cast=bool)
CSRF_REQUIRE_REFERER = config('CSRF_REQUIRE_REFERER', default=True, cast=bool)
CSRF_ALLOWED_ORIGINS = config('CSRF_ALLOWED_ORIGINS', default='localhost:3000,127.0.0.1:3000', cast=lambda v: [s.strip() for s in v.split(',')])

# Security Monitoring Configuration
BLOCK_SUSPICIOUS_REQUESTS = config('BLOCK_SUSPICIOUS_REQUESTS', default=False, cast=bool)

# PII Protection Configuration
PII_DETECTION_ENABLED = config('PII_DETECTION_ENABLED', default=True, cast=bool)
PII_AUTO_REDACTION = config('PII_AUTO_REDACTION', default=False, cast=bool)
PII_CLASSIFICATION_ML_ENABLED = config('PII_CLASSIFICATION_ML_ENABLED', default=False, cast=bool)

# GDPR Compliance Configuration
GDPR_COMPLIANCE_ENABLED = config('GDPR_COMPLIANCE_ENABLED', default=True, cast=bool)
GDPR_DEFAULT_RETENTION_DAYS = config('GDPR_DEFAULT_RETENTION_DAYS', default=2555, cast=int)  # 7 years
GDPR_AUTO_DELETION_ENABLED = config('GDPR_AUTO_DELETION_ENABLED', default=False, cast=bool)

# Data Subject Rights Configuration
DSAR_RESPONSE_DAYS = config('DSAR_RESPONSE_DAYS', default=30, cast=int)
DSAR_AUTO_FULFILLMENT = config('DSAR_AUTO_FULFILLMENT', default=False, cast=bool)

# Security Monitoring & Alerting
SECURITY_ALERT_EMAIL = config('SECURITY_ALERT_EMAIL', default='security@company.com')
SECURITY_ALERT_SLACK_WEBHOOK = config('SECURITY_ALERT_SLACK_WEBHOOK', default='')

# Brute Force Protection
BRUTE_FORCE_THRESHOLD = config('BRUTE_FORCE_THRESHOLD', default=5, cast=int)
BRUTE_FORCE_WINDOW_MINUTES = config('BRUTE_FORCE_WINDOW_MINUTES', default=15, cast=int)

# Session Security
SESSION_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_HTTPONLY = True
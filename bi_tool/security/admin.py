"""
Django admin configuration for security models.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from .models import AuditLog, EncryptionKey, SecurityConfiguration, SessionToken


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """Admin interface for audit logs."""
    
    list_display = ['timestamp', 'action', 'severity', 'resource_type', 'user_display', 'success', 'ip_address']
    list_filter = ['action', 'severity', 'success', 'resource_type', 'timestamp']
    search_fields = ['description', 'resource_id', 'user__username', 'ip_address']
    readonly_fields = ['timestamp', 'integrity_hash', 'id']
    ordering = ['-timestamp']
    date_hierarchy = 'timestamp'
    
    fieldsets = (
        ('Event Information', {
            'fields': ('timestamp', 'action', 'severity', 'resource_type', 'resource_id', 'success')
        }),
        ('User & Session', {
            'fields': ('user', 'session_id', 'ip_address', 'user_agent')
        }),
        ('Details', {
            'fields': ('description', 'metadata', 'correlation_id', 'request_id')
        }),
        ('Integrity', {
            'fields': ('integrity_hash',),
            'classes': ('collapse',)
        })
    )
    
    def user_display(self, obj):
        if obj.user:
            return f"{obj.user.username} ({obj.user.id})"
        return "Anonymous"
    user_display.short_description = "User"
    
    def has_delete_permission(self, request, obj=None):
        """Audit logs should not be deletable for integrity."""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Audit logs should not be editable for integrity."""
        return False


@admin.register(EncryptionKey)
class EncryptionKeyAdmin(admin.ModelAdmin):
    """Admin interface for encryption keys."""
    
    list_display = ['key_id', 'key_type', 'algorithm', 'version', 'is_active', 'created_at', 'expires_at']
    list_filter = ['key_type', 'algorithm', 'is_active', 'created_at']
    search_fields = ['key_id', 'description']
    readonly_fields = ['created_at', 'updated_at', 'usage_count', 'last_used']
    
    fieldsets = (
        ('Key Information', {
            'fields': ('key_id', 'key_type', 'algorithm', 'version', 'description')
        }),
        ('Configuration', {
            'fields': ('kms_key_id', 'is_active', 'expires_at')
        }),
        ('Usage Statistics', {
            'fields': ('usage_count', 'last_used'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('metadata',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def get_readonly_fields(self, request, obj=None):
        if obj:  # Editing existing object
            return self.readonly_fields + ['key_id', 'key_type', 'algorithm']
        return self.readonly_fields


@admin.register(SecurityConfiguration)
class SecurityConfigurationAdmin(admin.ModelAdmin):
    """Admin interface for security configuration."""
    
    list_display = ['config_key', 'config_type', 'is_active', 'updated_at', 'updated_by']
    list_filter = ['config_type', 'is_active', 'updated_at']
    search_fields = ['config_key', 'description']
    
    fieldsets = (
        ('Configuration', {
            'fields': ('config_key', 'config_type', 'config_value', 'description', 'is_active')
        }),
        ('Metadata', {
            'fields': ('metadata',),
            'classes': ('collapse',)
        }),
        ('Audit', {
            'fields': ('updated_by', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def save_model(self, request, obj, form, change):
        """Set the updated_by field to current user."""
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(SessionToken)
class SessionTokenAdmin(admin.ModelAdmin):
    """Admin interface for session tokens."""
    
    list_display = ['user', 'token_type', 'is_active', 'created_at', 'expires_at', 'last_used']
    list_filter = ['token_type', 'is_active', 'created_at']
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['token_hash', 'created_at', 'last_used']
    
    fieldsets = (
        ('Token Information', {
            'fields': ('user', 'token_type', 'token_hash', 'is_active')
        }),
        ('Validity', {
            'fields': ('created_at', 'expires_at', 'last_used')
        }),
        ('Metadata', {
            'fields': ('metadata',),
            'classes': ('collapse',)
        })
    )
    
    def get_queryset(self, request):
        """Only show active tokens by default."""
        qs = super().get_queryset(request)
        return qs.filter(is_active=True)


# Custom admin site configuration
admin.site.site_header = "BI Tool Security Administration"
admin.site.site_title = "BI Security Admin"
admin.site.index_title = "Security, Compliance & Data Privacy Management"
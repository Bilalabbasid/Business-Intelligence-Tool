from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from .models import User, UserSession


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    Custom admin interface for User model
    """
    list_display = ('username', 'email', 'role', 'branch_id', 'is_active', 'date_joined')
    list_filter = ('role', 'is_active', 'date_joined', 'branch_id')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    ordering = ('-date_joined',)
    
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name', 'email', 'phone_number', 'profile_picture')}),
        (_('Role & Branch'), {'fields': ('role', 'branch_id')}),
        (_('Permissions'), {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
        (_('Metadata'), {'fields': ('created_by',)}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2', 'role', 'branch_id'),
        }),
    )
    
    readonly_fields = ('date_joined', 'last_login', 'created_at', 'updated_at')
    
    def get_queryset(self, request):
        """
        Filter users based on admin's role
        """
        qs = super().get_queryset(request)
        
        # Super users can see all
        if request.user.is_superuser:
            return qs
        
        # Super admins can see all users
        if hasattr(request.user, 'role') and request.user.role == User.SUPER_ADMIN:
            return qs
        
        # Managers can only see users in their branch
        if hasattr(request.user, 'role') and request.user.role == User.MANAGER:
            return qs.filter(branch_id=request.user.branch_id)
        
        # Other roles can't access user admin
        return qs.none()


@admin.register(UserSession)
class UserSessionAdmin(admin.ModelAdmin):
    """
    Admin interface for UserSession model
    """
    list_display = ('user', 'ip_address', 'created_at', 'last_activity', 'is_active')
    list_filter = ('is_active', 'created_at', 'last_activity')
    search_fields = ('user__username', 'user__email', 'ip_address')
    readonly_fields = ('session_key', 'created_at', 'last_activity')
    ordering = ('-last_activity',)
    
    def get_queryset(self, request):
        """
        Filter sessions based on admin's permissions
        """
        qs = super().get_queryset(request)
        
        # Super users and super admins can see all sessions
        if request.user.is_superuser or (hasattr(request.user, 'role') and request.user.role == User.SUPER_ADMIN):
            return qs
        
        # Other users can only see their own sessions
        return qs.filter(user=request.user)


# Customize admin site header and title
admin.site.site_header = "BI Tool Administration"
admin.site.site_title = "BI Tool Admin"
admin.site.index_title = "Welcome to BI Tool Administration"
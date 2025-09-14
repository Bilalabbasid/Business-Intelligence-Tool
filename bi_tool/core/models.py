from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone
import uuid


class BaseModel(models.Model):
    """
    Abstract base model with common fields for all models.
    """
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        abstract = True


class UserManager(BaseUserManager):
    """
    Custom user manager for the User model
    """
    
    def create_user(self, username, email, password=None, **extra_fields):
        """
        Create and return a regular user with the given username, email, and password.
        """
        if not username:
            raise ValueError('The Username field must be set')
        if not email:
            raise ValueError('The Email field must be set')
            
        email = self.normalize_email(email)
        user = self.model(username=username, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, username, email, password=None, **extra_fields):
        """
        Create and return a superuser with the given username, email, and password.
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', User.SUPER_ADMIN)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
            
        return self.create_user(username, email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """
    Custom User model with role-based access control for BI tool
    """
    
    # Role choices for the BI tool
    SUPER_ADMIN = 'super_admin'
    MANAGER = 'manager'
    ANALYST = 'analyst'
    STAFF = 'staff'
    
    ROLE_CHOICES = [
        (SUPER_ADMIN, 'Super Admin'),
        (MANAGER, 'Branch Manager'),
        (ANALYST, 'Analyst'),
        (STAFF, 'Staff'),
    ]
    
    # Primary fields
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    
    # Role and branch association
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default=STAFF,
        help_text='User role determines access permissions'
    )
    branch_id = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text='Branch identifier for managers and staff (null for super admins and analysts)'
    )
    
    # Status fields
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)
    last_login = models.DateTimeField(null=True, blank=True)
    
    # Additional profile fields
    phone_number = models.CharField(max_length=15, blank=True)
    profile_picture = models.URLField(blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_users'
    )
    
    objects = UserManager()
    
    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email']
    
    class Meta:
        db_table = 'users'
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        indexes = [
            models.Index(fields=['username']),
            models.Index(fields=['email']),
            models.Index(fields=['role']),
            models.Index(fields=['branch_id']),
        ]
    
    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"
    
    @property
    def full_name(self):
        """Return the full name of the user."""
        return f"{self.first_name} {self.last_name}".strip()
    
    def has_role(self, role):
        """Check if user has a specific role."""
        return self.role == role
    
    def is_super_admin(self):
        """Check if user is a super admin."""
        return self.role == self.SUPER_ADMIN
    
    def is_manager(self):
        """Check if user is a branch manager."""
        return self.role == self.MANAGER
    
    def is_analyst(self):
        """Check if user is an analyst."""
        return self.role == self.ANALYST
    
    def is_staff_member(self):
        """Check if user is staff (not to be confused with Django's is_staff)."""
        return self.role == self.STAFF
    
    def can_access_branch(self, branch_id):
        """
        Check if user can access data for a specific branch.
        Super admins can access all branches.
        Managers and staff can only access their assigned branch.
        Analysts can access all branches for reporting purposes.
        """
        if self.is_super_admin() or self.is_analyst():
            return True
        return self.branch_id == branch_id
    
    def get_accessible_branches(self):
        """
        Return list of branch IDs the user can access.
        """
        if self.is_super_admin() or self.is_analyst():
            # Return all branches (this would need to be implemented based on your branch model)
            return None  # None means all branches
        return [self.branch_id] if self.branch_id else []
    
    def clean(self):
        """
        Validate the model data.
        """
        from django.core.exceptions import ValidationError
        
        # Managers and staff must have a branch_id
        if self.role in [self.MANAGER, self.STAFF] and not self.branch_id:
            raise ValidationError({
                'branch_id': f'{self.get_role_display()} must be assigned to a branch.'
            })
        
        # Super admins and analysts should not have branch_id
        if self.role in [self.SUPER_ADMIN, self.ANALYST] and self.branch_id:
            raise ValidationError({
                'branch_id': f'{self.get_role_display()} should not be assigned to a specific branch.'
            })


class UserSession(models.Model):
    """
    Track active user sessions for security and analytics
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sessions')
    session_key = models.CharField(max_length=255, unique=True)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'user_sessions'
        ordering = ['-last_activity']
    
    def __str__(self):
        return f"{self.user.username} - {self.ip_address} - {self.created_at}"
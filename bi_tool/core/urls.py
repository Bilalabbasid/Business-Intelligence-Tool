from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import views

app_name = 'core'

urlpatterns = [
    # Authentication endpoints
    path('register/', views.UserRegistrationView.as_view(), name='user-register'),
    path('login/', views.CustomTokenObtainPairView.as_view(), name='user-login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path('logout/', views.LogoutView.as_view(), name='user-logout'),
    
    # User profile endpoints
    path('profile/', views.UserProfileView.as_view(), name='user-profile'),
    path('password-change/', views.PasswordChangeView.as_view(), name='password-change'),
    path('sessions/', views.user_sessions_view, name='user-sessions'),
    
    # Admin-only user management endpoints
    path('users/', views.UserListView.as_view(), name='user-list'),
    path('users/create/', views.UserCreateByAdminView.as_view(), name='user-create-admin'),
]
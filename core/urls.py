from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('register/', views.register, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('service/open/', views.open_service, name='open_service'),
    path('service/close/', views.close_service, name='close_service'),
    
    # Validation URLs
    path('validations/pending/', views.pending_validations, name='pending_validations'),
    path('action/<int:action_id>/validate/', views.validate_action, name='validate_action'),
    path('action/<int:action_id>/reject/', views.reject_action, name='reject_action'),
    path('action/<int:action_id>/comment/', views.comment_action, name='comment_action'),
    path('action/<int:action_id>/history/', views.validation_history, name='validation_history'),
    
    # Consultation URLs
    path('consultation/actions/', views.global_actions_view, name='global_actions'),
    path('consultation/services/', views.global_services_view, name='global_services'),
    path('consultation/validations/', views.global_validations_view, name='global_validations'),
    
    # Profile URLs
    path('profile/', views.user_profile_view, name='user_profile_self'),
    path('profile/<str:username>/', views.user_profile_view, name='user_profile'),
    
    # Action Management URLs
    path('actions/', views.action_list, name='action_list'),
    path('action/create/', views.action_create, name='action_create'),
    path('action/<int:action_id>/edit/', views.action_edit, name='action_edit'),
    
    # Notification URLs
    path('notifications/', views.notifications_list, name='notifications_list'),
    path('notifications/<int:notif_id>/read/', views.mark_notification_read, name='mark_notification_read'),
    path('notifications/read-all/', views.mark_all_notifications_read, name='mark_all_notifications_read'),
    path('notifications/<int:notif_id>/delete/', views.delete_notification, name='delete_notification'),
    path('api/notifications/unread-count/', views.get_unread_count, name='unread_count'),
    
    # User Mention API
    path('api/users/search/', views.user_search_api, name='user_search_api'),
]

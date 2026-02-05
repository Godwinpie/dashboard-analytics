# urls.py
from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    # Invitation URLs
    path('invite/', views.InviteUserView.as_view(), name='invite_user'),
    path('manage-users/', views.ManageUsersListView.as_view(), name='manage_users_list'),
    path('manage-access/<int:user_id>/', views.ManageUserAccessView.as_view(), name='manage_user_access'),
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
]


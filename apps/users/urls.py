from django.urls import path

from .views import LoginView, LogoutView, RefreshView, RegisterView

app_name = 'users'

urlpatterns = [
    path('register', RegisterView.as_view(), name='register'),
    path('register/', RegisterView.as_view(), name='register_slash'),
    path('login', LoginView.as_view(), name='login'),
    path('login/', LoginView.as_view(), name='login_slash'),
    path('refresh', RefreshView.as_view(), name='refresh'),
    path('refresh/', RefreshView.as_view(), name='refresh_slash'),
    path('logout', LogoutView.as_view(), name='logout'),
    path('logout/', LogoutView.as_view(), name='logout_slash'),
]

from django.urls import path

from .views import LoginView, RegisterView

app_name = 'users'

urlpatterns = [
    path('register', RegisterView.as_view(), name='register'),
    path('register/', RegisterView.as_view(), name='register_slash'),
    path('login', LoginView.as_view(), name='login'),
    path('login/', LoginView.as_view(), name='login_slash'),
]

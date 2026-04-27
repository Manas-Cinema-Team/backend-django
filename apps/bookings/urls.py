from django.urls import path

from .views import BookingConfirmView, BookingCreateView, BookingDetailView

app_name = 'bookings'

urlpatterns = [
    path('', BookingCreateView.as_view(), name='create'),
    path('<int:pk>/', BookingDetailView.as_view(), name='detail'),
    path('<int:pk>/confirm/', BookingConfirmView.as_view(), name='confirm'),
]

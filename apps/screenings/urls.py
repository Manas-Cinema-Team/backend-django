from django.urls import path

from .views import SessionDetailView, SessionListView, SessionSeatMapView

app_name = 'screenings'

urlpatterns = [
    path('', SessionListView.as_view(), name='list'),
    path('<int:pk>/', SessionDetailView.as_view(), name='detail'),
    path('<int:pk>/seats/', SessionSeatMapView.as_view(), name='seat_map'),
]

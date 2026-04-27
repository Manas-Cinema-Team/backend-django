from django.urls import path

from .views import MovieDetailView, MovieListView

app_name = 'movies'

urlpatterns = [
    path('', MovieListView.as_view(), name='list'),
    path('<int:pk>/', MovieDetailView.as_view(), name='detail'),
]

from django.db.models import Prefetch, Q
from django.utils import timezone
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.screenings.querysets import content_session_queryset
from core.api import not_found_response, validation_error_response
from core.pagination import DefaultPagination

from .models import Movie
from .serializers import MovieDetailSerializer, MovieListQuerySerializer, MovieListSerializer


class MovieListView(APIView):
    permission_classes = [AllowAny]
    pagination_class = DefaultPagination

    def get(self, request):
        query_serializer = MovieListQuerySerializer(data=request.query_params)
        if not query_serializer.is_valid():
            return validation_error_response(query_serializer.errors)

        queryset = Movie.objects.filter(is_active=True).order_by('title')
        genre = query_serializer.validated_data.get('genre')
        search = query_serializer.validated_data.get('search')

        if genre:
            queryset = queryset.filter(genre=genre)

        if search:
            queryset = queryset.filter(Q(title__icontains=search) | Q(description__icontains=search))

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request, view=self)
        serializer = MovieListSerializer(page, many=True)

        return paginator.get_paginated_response(serializer.data)


class MovieDetailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, pk: int):
        session_queryset = content_session_queryset().filter(
            is_active=True,
            start_datetime__gte=timezone.now(),
        )
        movie = (
            Movie.objects.filter(pk=pk, is_active=True)
            .prefetch_related(Prefetch('sessions', queryset=session_queryset, to_attr='api_sessions'))
            .first()
        )

        if movie is None:
            return not_found_response('Фильм не найден')

        serializer = MovieDetailSerializer(movie)
        return Response(serializer.data)

from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api import not_found_response, validation_error_response
from core.pagination import DefaultPagination

from .querysets import content_session_queryset
from .serializers import SeatMapSerializer, SessionContentSerializer, SessionListQuerySerializer
from .services import build_session_seat_map


class SessionListView(APIView):
    permission_classes = [AllowAny]
    pagination_class = DefaultPagination

    def get(self, request):
        query_serializer = SessionListQuerySerializer(data=request.query_params)
        if not query_serializer.is_valid():
            return validation_error_response(query_serializer.errors)

        queryset = content_session_queryset().order_by('start_datetime')
        date = query_serializer.validated_data.get('date')
        movie_id = query_serializer.validated_data.get('movie_id')
        hall_id = query_serializer.validated_data.get('hall_id')

        if date is not None:
            queryset = queryset.filter(start_datetime__date=date)

        if movie_id is not None:
            queryset = queryset.filter(movie_id=movie_id)

        if hall_id is not None:
            queryset = queryset.filter(hall_id=hall_id)

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request, view=self)
        serializer = SessionContentSerializer(page, many=True)

        return paginator.get_paginated_response(serializer.data)


class SessionDetailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, pk: int):
        session = content_session_queryset().filter(pk=pk).first()
        if session is None:
            return not_found_response('Сеанс не найден')

        serializer = SessionContentSerializer(session)
        return Response(serializer.data)


class SessionSeatMapView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, pk: int):
        session = content_session_queryset().filter(pk=pk).first()
        if session is None:
            return not_found_response('Сеанс не найден')

        payload = build_session_seat_map(session, user=request.user)
        serializer = SeatMapSerializer(payload)
        return Response(serializer.data)

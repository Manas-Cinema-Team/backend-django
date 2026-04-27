from rest_framework import serializers

from .models import MovieSession
from .services import build_session_seat_map, get_price_payload


class SessionListQuerySerializer(serializers.Serializer):
    date = serializers.DateField(required=False)
    movie_id = serializers.IntegerField(required=False, min_value=1)
    hall_id = serializers.IntegerField(required=False, min_value=1)

    def to_internal_value(self, data):
        normalized_data = data.copy()
        for field in ('date', 'movie_id', 'hall_id'):
            if normalized_data.get(field) == '':
                normalized_data.pop(field)

        return super().to_internal_value(normalized_data)


class SessionMovieSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    title = serializers.CharField()
    poster_url = serializers.CharField()
    duration = serializers.IntegerField()
    age_rating = serializers.CharField()


class SessionHallSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    rows = serializers.IntegerField()
    seats_per_row = serializers.IntegerField()


class PriceSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, coerce_to_string=False)
    currency = serializers.CharField()


class SessionContentSerializer(serializers.ModelSerializer):
    movie = serializers.SerializerMethodField()
    hall = serializers.SerializerMethodField()
    price = serializers.SerializerMethodField()
    available_seats = serializers.SerializerMethodField()

    class Meta:
        model = MovieSession
        fields = (
            'id',
            'movie',
            'hall',
            'start_datetime',
            'end_datetime',
            'price',
            'is_active',
            'available_seats',
        )

    def get_movie(self, obj):
        return SessionMovieSerializer(
            {
                'id': obj.movie_id,
                'title': obj.movie.title,
                'poster_url': obj.movie.poster_url,
                'duration': obj.movie.duration,
                'age_rating': obj.movie.age_rating,
            }
        ).data

    def get_hall(self, obj):
        return SessionHallSerializer(
            {
                'id': obj.hall_id,
                'name': obj.hall.name,
                'rows': obj.hall.rows,
                'seats_per_row': obj.hall.seats_per_row,
            }
        ).data

    def get_price(self, obj):
        payload = get_price_payload(obj)
        if payload is None:
            return None
        return PriceSerializer(payload).data

    def get_available_seats(self, obj):
        return build_session_seat_map(obj)['available_seats']


class SeatSerializer(serializers.Serializer):
    row = serializers.IntegerField()
    number = serializers.IntegerField()
    type = serializers.CharField()
    status = serializers.CharField()
    held_by_me = serializers.BooleanField()
    expires_at = serializers.DateTimeField(allow_null=True)
    price = PriceSerializer(allow_null=True)


class SeatSchemaSerializer(serializers.Serializer):
    rows = serializers.ListField()
    disabled_seats = serializers.ListField()


class SeatMapSerializer(serializers.Serializer):
    hall_id = serializers.IntegerField()
    hall_name = serializers.CharField()
    schema = SeatSchemaSerializer()
    seats = SeatSerializer(many=True)
    polling_interval = serializers.IntegerField()

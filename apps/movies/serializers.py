from django.utils import timezone
from rest_framework import serializers

from .models import Movie, MovieGenre


class MovieListQuerySerializer(serializers.Serializer):
    genre = serializers.ChoiceField(choices=MovieGenre.choices, required=False, allow_blank=True)
    search = serializers.CharField(required=False, allow_blank=True, max_length=255)

    def to_internal_value(self, data):
        normalized_data = data.copy()
        for field in ('genre', 'search'):
            if normalized_data.get(field) == '':
                normalized_data.pop(field)

        return super().to_internal_value(normalized_data)


class MovieListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Movie
        fields = (
            'id',
            'title',
            'description',
            'genre',
            'duration',
            'age_rating',
            'poster_url',
            'release_date',
            'is_active',
        )


class MovieDetailSerializer(MovieListSerializer):
    sessions = serializers.SerializerMethodField()

    class Meta(MovieListSerializer.Meta):
        fields = MovieListSerializer.Meta.fields + ('sessions',)

    def get_sessions(self, obj):
        from apps.screenings.serializers import SessionContentSerializer

        sessions = getattr(obj, 'api_sessions', [])
        active_sessions = [session for session in sessions if session.is_active and session.start_datetime >= timezone.now()]

        return SessionContentSerializer(active_sessions, many=True).data

from datetime import timedelta

from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from apps.halls.models import Hall
from apps.movies.models import AgeRating, Movie, MovieGenre
from apps.screenings.models import MovieSession


class MovieSessionModelTests(TestCase):
    def test_session_end_must_be_after_start(self):
        movie = Movie.objects.create(
            title='Arrival',
            description='Sci-fi drama.',
            genre=MovieGenre.SCI_FI,
            duration=116,
            age_rating=AgeRating.AGE_12,
            release_date=timezone.now().date(),
        )
        hall = Hall.objects.create(name='Hall 1', rows=10, seats_per_row=12)
        start = timezone.now()

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                MovieSession.objects.create(
                    movie=movie,
                    hall=hall,
                    start_datetime=start,
                    end_datetime=start - timedelta(minutes=1),
                )

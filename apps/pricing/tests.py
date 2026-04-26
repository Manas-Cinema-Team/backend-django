from datetime import timedelta

from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from apps.halls.models import Hall
from apps.movies.models import AgeRating, Movie, MovieGenre
from apps.pricing.models import TicketCurrency, TicketPrice
from apps.screenings.models import MovieSession


class TicketPriceModelTests(TestCase):
    def test_session_currency_must_be_unique(self):
        movie = Movie.objects.create(
            title='Dune',
            description='Epic sci-fi.',
            genre=MovieGenre.SCI_FI,
            duration=155,
            age_rating=AgeRating.AGE_12,
            release_date=timezone.now().date(),
        )
        hall = Hall.objects.create(name='Hall 2', rows=8, seats_per_row=14)
        start = timezone.now()
        session = MovieSession.objects.create(
            movie=movie,
            hall=hall,
            start_datetime=start,
            end_datetime=start + timedelta(hours=3),
        )

        TicketPrice.objects.create(
            session=session,
            amount='450.00',
            currency=TicketCurrency.KGS,
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                TicketPrice.objects.create(
                    session=session,
                    amount='500.00',
                    currency=TicketCurrency.KGS,
                )

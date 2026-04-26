from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from apps.bookings.models import Booking, BookingSeat, SeatHold, SeatHoldStatus
from apps.halls.models import Hall
from apps.movies.models import AgeRating, Movie, MovieGenre
from apps.screenings.models import MovieSession

User = get_user_model()


class BookingModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='booking@example.com', password='strongpass123')
        self.movie = Movie.objects.create(
            title='Interstellar',
            description='Space exploration.',
            genre=MovieGenre.SCI_FI,
            duration=169,
            age_rating=AgeRating.AGE_12,
            release_date=timezone.now().date(),
        )
        self.hall = Hall.objects.create(name='Hall 3', rows=12, seats_per_row=16)
        start = timezone.now()
        self.session = MovieSession.objects.create(
            movie=self.movie,
            hall=self.hall,
            start_datetime=start,
            end_datetime=start + timedelta(hours=3),
        )

    def test_active_hold_for_same_seat_must_be_unique(self):
        SeatHold.objects.create(
            session=self.session,
            user=self.user,
            seat_row=4,
            seat_number=7,
            expires_at=timezone.now() + timedelta(minutes=10),
            status=SeatHoldStatus.HELD,
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                SeatHold.objects.create(
                    session=self.session,
                    user=self.user,
                    seat_row=4,
                    seat_number=7,
                    expires_at=timezone.now() + timedelta(minutes=10),
                    status=SeatHoldStatus.HELD,
                )

    def test_booking_seat_must_be_unique_inside_booking(self):
        booking = Booking.objects.create(
            session=self.session,
            user=self.user,
            total_amount='900.00',
        )
        BookingSeat.objects.create(
            booking=booking,
            seat_row=2,
            seat_number=5,
            price_at_booking='450.00',
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                BookingSeat.objects.create(
                    booking=booking,
                    seat_row=2,
                    seat_number=5,
                    price_at_booking='450.00',
                )

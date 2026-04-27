from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.bookings.models import Booking, BookingSeat, BookingStatus, PaymentStatus, SeatHold, SeatHoldStatus
from apps.halls.models import Hall
from apps.movies.models import AgeRating, Movie, MovieGenre
from apps.pricing.models import TicketCurrency, TicketPrice
from apps.screenings.models import MovieSession

User = get_user_model()


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


class SessionApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='seats@example.com', password='strongpass123')
        self.other_user = User.objects.create_user(email='other@example.com', password='strongpass123')
        self.movie = Movie.objects.create(
            title='Interstellar',
            description='Space exploration.',
            genre=MovieGenre.SCI_FI,
            duration=169,
            age_rating=AgeRating.AGE_12,
            poster_url='https://example.com/interstellar.jpg',
            release_date=timezone.now().date(),
            is_active=True,
        )
        self.other_movie = Movie.objects.create(
            title='Comedy Night',
            description='Light comedy.',
            genre=MovieGenre.COMEDY,
            duration=101,
            age_rating=AgeRating.AGE_12,
            poster_url='https://example.com/comedy.jpg',
            release_date=timezone.now().date(),
            is_active=True,
        )
        self.hall = Hall.objects.create(
            name='Screening API Hall',
            rows=1,
            seats_per_row=4,
            schema_metadata={
                'rows': [
                    {
                        'row': 1,
                        'seats': [
                            {'number': 1, 'type': 'standard'},
                            {'number': 2, 'type': 'standard'},
                            {'number': 3, 'type': 'vip'},
                            {'number': 4, 'type': 'standard'},
                        ],
                    }
                ],
                'disabled_seats': [
                    {'row': 1, 'number': 4},
                ],
            },
        )
        self.other_hall = Hall.objects.create(name='Screening Filter Hall', rows=2, seats_per_row=3)
        start = timezone.now() + timedelta(days=1)
        self.session = MovieSession.objects.create(
            movie=self.movie,
            hall=self.hall,
            start_datetime=start,
            end_datetime=start + timedelta(hours=3),
            is_active=True,
        )
        TicketPrice.objects.create(
            session=self.session,
            amount='450.00',
            currency=TicketCurrency.KGS,
        )
        self.other_session = MovieSession.objects.create(
            movie=self.other_movie,
            hall=self.other_hall,
            start_datetime=start + timedelta(days=1),
            end_datetime=start + timedelta(days=1, hours=2),
            is_active=True,
        )
        TicketPrice.objects.create(
            session=self.other_session,
            amount='390.00',
            currency=TicketCurrency.KGS,
        )
        self.inactive_session = MovieSession.objects.create(
            movie=self.movie,
            hall=self.hall,
            start_datetime=start + timedelta(days=2),
            end_datetime=start + timedelta(days=2, hours=3),
            is_active=False,
        )
        TicketPrice.objects.create(
            session=self.inactive_session,
            amount='500.00',
            currency=TicketCurrency.KGS,
        )
        SeatHold.objects.create(
            session=self.session,
            user=self.user,
            seat_row=1,
            seat_number=2,
            expires_at=timezone.now() + timedelta(minutes=10),
            status=SeatHoldStatus.HELD,
        )
        booking = Booking.objects.create(
            session=self.session,
            user=self.other_user,
            total_amount='450.00',
            booking_status=BookingStatus.CONFIRMED,
            payment_status=PaymentStatus.PAID,
            confirmed_at=timezone.now(),
        )
        BookingSeat.objects.create(
            booking=booking,
            seat_row=1,
            seat_number=3,
            price_at_booking='450.00',
        )

    def test_sessions_list_returns_paginated_active_sessions_and_supports_filters(self):
        response = self.client.get(
            '/api/v1/sessions/',
            {
                'date': self.session.start_datetime.date().isoformat(),
                'movie_id': self.movie.id,
                'hall_id': self.hall.id,
                'page': 1,
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(len(response.data['results']), 1)
        result = response.data['results'][0]
        self.assertEqual(result['id'], self.session.id)
        self.assertEqual(result['available_seats'], 1)
        self.assertEqual(result['price']['amount'], 450.0)
        self.assertEqual(result['price']['currency'], 'KGS')

    def test_session_detail_returns_active_session(self):
        response = self.client.get(f'/api/v1/sessions/{self.session.id}/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.session.id)
        self.assertEqual(response.data['available_seats'], 1)
        self.assertEqual(response.data['movie']['title'], self.movie.title)
        self.assertEqual(response.data['hall']['name'], self.hall.name)

    def test_session_detail_returns_not_found_for_inactive_session(self):
        response = self.client.get(f'/api/v1/sessions/{self.inactive_session.id}/')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data['error'], 'NOT_FOUND')
        self.assertEqual(response.data['message'], 'Сеанс не найден')

    def test_session_seats_returns_seat_statuses(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(f'/api/v1/sessions/{self.session.id}/seats/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['hall_id'], self.hall.id)
        self.assertEqual(response.data['polling_interval'], 5)

        seats = {(seat['row'], seat['number']): seat for seat in response.data['seats']}
        self.assertEqual(seats[(1, 1)]['status'], 'available')
        self.assertEqual(seats[(1, 2)]['status'], 'held')
        self.assertTrue(seats[(1, 2)]['held_by_me'])
        self.assertIsNotNone(seats[(1, 2)]['expires_at'])
        self.assertEqual(seats[(1, 3)]['status'], 'booked')
        self.assertFalse(seats[(1, 3)]['held_by_me'])
        self.assertEqual(seats[(1, 4)]['status'], 'disabled')
        self.assertEqual(seats[(1, 3)]['price']['amount'], 450.0)
        self.assertEqual(seats[(1, 3)]['price']['currency'], 'KGS')

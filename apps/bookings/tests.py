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


class BookingWorkflowApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='booking-api@example.com', password='strongpass123')
        self.other_user = User.objects.create_user(email='booking-other@example.com', password='strongpass123')
        self.movie = Movie.objects.create(
            title='Dune: Part Two',
            description='Epic sci-fi saga.',
            genre=MovieGenre.SCI_FI,
            duration=166,
            age_rating=AgeRating.AGE_12,
            poster_url='https://example.com/dune-2.jpg',
            release_date=timezone.now().date(),
            is_active=True,
        )
        self.hall = Hall.objects.create(
            name='Booking Workflow Hall',
            rows=2,
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
                    },
                    {
                        'row': 2,
                        'seats': [
                            {'number': 1, 'type': 'standard'},
                            {'number': 2, 'type': 'standard'},
                            {'number': 3, 'type': 'standard'},
                            {'number': 4, 'type': 'standard'},
                        ],
                    },
                ],
                'disabled_seats': [
                    {'row': 2, 'number': 4},
                ],
            },
        )
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

    def test_create_booking_requires_authentication(self):
        response = self.client.post(
            '/api/v1/bookings/',
            {
                'session_id': self.session.id,
                'seats': [{'row': 1, 'number': 1}],
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.data['error'], 'UNAUTHORIZED')

    def test_create_booking_creates_hold_and_returns_draft_booking(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            '/api/v1/bookings/',
            {
                'session_id': self.session.id,
                'seats': [
                    {'row': 1, 'number': 1},
                    {'row': 1, 'number': 3},
                ],
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['session']['id'], self.session.id)
        self.assertEqual(response.data['session']['movie']['title'], self.movie.title)
        self.assertEqual(response.data['session']['hall']['name'], self.hall.name)
        self.assertEqual(response.data['booking_status'], 'draft')
        self.assertEqual(response.data['payment_status'], 'pending')
        self.assertEqual(response.data['currency'], 'KGS')
        self.assertEqual(response.data['total_amount'], 900.0)
        self.assertIsNotNone(response.data['expires_at'])
        self.assertEqual(
            response.data['seats'],
            [
                {'row': 1, 'number': 1, 'type': 'standard', 'price_at_booking': 450.0},
                {'row': 1, 'number': 3, 'type': 'vip', 'price_at_booking': 450.0},
            ],
        )

        booking = Booking.objects.get(pk=response.data['id'])
        self.assertEqual(booking.booking_status, BookingStatus.PENDING)
        self.assertEqual(booking.payment_status, PaymentStatus.PENDING)
        self.assertEqual(booking.currency, TicketCurrency.KGS)
        self.assertIsNotNone(booking.expires_at)
        self.assertGreater(booking.expires_at, timezone.now())
        self.assertEqual(booking.seat_holds.count(), 2)
        self.assertEqual(
            list(
                booking.seat_holds.order_by('seat_row', 'seat_number').values_list(
                    'seat_row',
                    'seat_number',
                    'status',
                )
            ),
            [
                (1, 1, SeatHoldStatus.HELD),
                (1, 3, SeatHoldStatus.HELD),
            ],
        )

    def test_create_booking_returns_conflict_with_conflicting_seats(self):
        SeatHold.objects.create(
            session=self.session,
            user=self.other_user,
            seat_row=1,
            seat_number=2,
            expires_at=timezone.now() + timedelta(minutes=10),
            status=SeatHoldStatus.HELD,
        )
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            '/api/v1/bookings/',
            {
                'session_id': self.session.id,
                'seats': [
                    {'row': 1, 'number': 1},
                    {'row': 1, 'number': 2},
                ],
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(response.data['error'], 'SEAT_HELD')
        self.assertEqual(response.data['details'], {'seats': [{'row': 1, 'number': 2}]})

    def test_get_booking_returns_current_state_for_owner(self):
        booking = self._create_draft_booking(user=self.user, seats=[(1, 1), (1, 2)])
        self.client.force_authenticate(user=self.user)

        response = self.client.get(f'/api/v1/bookings/{booking.id}/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], booking.id)
        self.assertEqual(response.data['booking_status'], 'draft')
        self.assertEqual(
            response.data['seats'],
            [
                {'row': 1, 'number': 1, 'type': 'standard', 'price_at_booking': 450.0},
                {'row': 1, 'number': 2, 'type': 'standard', 'price_at_booking': 450.0},
            ],
        )

    def test_confirm_booking_marks_booking_paid_and_creates_booking_seats(self):
        booking = self._create_draft_booking(user=self.user, seats=[(1, 1), (1, 3)])
        self.client.force_authenticate(user=self.user)

        response = self.client.post(f'/api/v1/bookings/{booking.id}/confirm/', {}, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['booking_status'], 'confirmed')
        self.assertEqual(response.data['payment_status'], 'paid')
        self.assertIsNotNone(response.data['confirmed_at'])

        booking.refresh_from_db()
        self.assertEqual(booking.booking_status, BookingStatus.CONFIRMED)
        self.assertEqual(booking.payment_status, PaymentStatus.PAID)
        self.assertIsNotNone(booking.confirmed_at)
        self.assertEqual(booking.seats.count(), 2)
        self.assertEqual(
            list(
                booking.seats.order_by('seat_row', 'seat_number').values_list(
                    'seat_row',
                    'seat_number',
                    'price_at_booking',
                )
            ),
            [
                (1, 1, 450),
                (1, 3, 450),
            ],
        )
        self.assertEqual(
            list(booking.seat_holds.values_list('status', flat=True).order_by('seat_row', 'seat_number')),
            [SeatHoldStatus.BOOKED, SeatHoldStatus.BOOKED],
        )

    def test_confirm_booking_returns_hold_expired_when_hold_is_stale(self):
        booking = self._create_draft_booking(
            user=self.user,
            seats=[(1, 1)],
            expires_at=timezone.now() - timedelta(minutes=1),
        )
        booking.seat_holds.update(expires_at=timezone.now() - timedelta(minutes=1))
        self.client.force_authenticate(user=self.user)

        response = self.client.post(f'/api/v1/bookings/{booking.id}/confirm/', {}, format='json')

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(response.data['error'], 'HOLD_EXPIRED')
        self.assertEqual(response.data['message'], 'Время ожидания истекло')

        booking.refresh_from_db()
        self.assertEqual(booking.booking_status, BookingStatus.EXPIRED)
        self.assertEqual(booking.payment_status, PaymentStatus.CANCELLED)
        self.assertEqual(
            list(booking.seat_holds.values_list('status', flat=True)),
            [SeatHoldStatus.EXPIRED],
        )

    def test_delete_booking_cancels_confirmed_booking_and_releases_seats(self):
        booking = self._create_draft_booking(user=self.user, seats=[(1, 1)])
        booking.booking_status = BookingStatus.CONFIRMED
        booking.payment_status = PaymentStatus.PAID
        booking.confirmed_at = timezone.now()
        booking.save(update_fields=['booking_status', 'payment_status', 'confirmed_at'])
        booking.seat_holds.update(status=SeatHoldStatus.BOOKED)
        BookingSeat.objects.create(
            booking=booking,
            seat_row=1,
            seat_number=1,
            price_at_booking='450.00',
        )

        self.client.force_authenticate(user=self.user)
        response = self.client.delete(f'/api/v1/bookings/{booking.id}/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {'message': 'Cancelled'})

        booking.refresh_from_db()
        self.assertEqual(booking.booking_status, BookingStatus.CANCELLED)
        self.assertEqual(booking.payment_status, PaymentStatus.CANCELLED)
        self.assertEqual(
            list(booking.seat_holds.values_list('status', flat=True)),
            [SeatHoldStatus.CANCELLED],
        )

        seat_map_response = self.client.get(f'/api/v1/sessions/{self.session.id}/seats/')
        seats = {
            (seat['row'], seat['number']): seat
            for seat in seat_map_response.data['seats']
        }
        self.assertEqual(seats[(1, 1)]['status'], 'available')

    def test_delete_foreign_booking_returns_forbidden(self):
        booking = self._create_draft_booking(user=self.user, seats=[(1, 1)])
        self.client.force_authenticate(user=self.other_user)

        response = self.client.delete(f'/api/v1/bookings/{booking.id}/')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data['error'], 'FORBIDDEN')

    def test_session_seat_map_expires_stale_hold_before_response(self):
        booking = self._create_draft_booking(
            user=self.user,
            seats=[(1, 2)],
            expires_at=timezone.now() - timedelta(minutes=1),
        )
        booking.seat_holds.update(expires_at=timezone.now() - timedelta(minutes=1))

        response = self.client.get(f'/api/v1/sessions/{self.session.id}/seats/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        seats = {
            (seat['row'], seat['number']): seat
            for seat in response.data['seats']
        }
        self.assertEqual(seats[(1, 2)]['status'], 'available')

        booking.refresh_from_db()
        self.assertEqual(booking.booking_status, BookingStatus.EXPIRED)
        self.assertEqual(
            list(booking.seat_holds.values_list('status', flat=True)),
            [SeatHoldStatus.EXPIRED],
        )

    def _create_draft_booking(self, *, user, seats, expires_at=None):
        expires_at = expires_at or (timezone.now() + timedelta(minutes=10))
        booking = Booking.objects.create(
            session=self.session,
            user=user,
            total_amount='450.00' if len(seats) == 1 else f'{450 * len(seats)}.00',
            currency=TicketCurrency.KGS,
            booking_status=BookingStatus.PENDING,
            payment_status=PaymentStatus.PENDING,
            expires_at=expires_at,
        )
        SeatHold.objects.bulk_create(
            [
                SeatHold(
                    booking=booking,
                    session=self.session,
                    user=user,
                    seat_row=row,
                    seat_number=number,
                    expires_at=expires_at,
                    status=SeatHoldStatus.HELD,
                )
                for row, number in seats
            ]
        )
        return booking

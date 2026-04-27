from django.db.models import Prefetch

from apps.bookings.models import Booking, BookingStatus, SeatHold, SeatHoldStatus

from .models import MovieSession


def content_session_queryset():
    confirmed_bookings = Booking.objects.filter(
        booking_status=BookingStatus.CONFIRMED,
    ).prefetch_related('seats')

    return MovieSession.objects.filter(is_active=True).select_related('movie', 'hall').prefetch_related(
        'ticket_prices',
        Prefetch(
            'seat_holds',
            queryset=SeatHold.objects.filter(
                status__in=[SeatHoldStatus.HELD, SeatHoldStatus.BOOKED],
            ).select_related('user'),
        ),
        Prefetch('bookings', queryset=confirmed_bookings),
    )

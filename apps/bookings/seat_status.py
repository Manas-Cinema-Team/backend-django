import logging

from django.conf import settings
from django.utils import timezone

from .models import Booking, BookingStatus, PaymentStatus, SeatHold, SeatHoldStatus

from apps.screenings.services import get_hall_layout, get_price_payload


logger = logging.getLogger('bookings')


def cleanup_expired_session_holds(session_id: int, now=None) -> list[int]:
    now = now or timezone.now()
    expired_booking_ids = list(
        SeatHold.objects.filter(
            session_id=session_id,
            booking_id__isnull=False,
            status=SeatHoldStatus.HELD,
            expires_at__lte=now,
        )
        .values_list('booking_id', flat=True)
        .distinct()
    )

    if expired_booking_ids:
        Booking.objects.filter(
            id__in=expired_booking_ids,
            booking_status=BookingStatus.PENDING,
        ).update(
            booking_status=BookingStatus.EXPIRED,
            payment_status=PaymentStatus.CANCELLED,
        )
        SeatHold.objects.filter(
            booking_id__in=expired_booking_ids,
            status=SeatHoldStatus.HELD,
        ).update(status=SeatHoldStatus.EXPIRED)
        logger.info(
            'booking_holds_expired session_id=%s booking_ids=%s expired_at=%s',
            session_id,
            expired_booking_ids,
            now.isoformat(),
        )

    orphan_expired_count = SeatHold.objects.filter(
        booking__isnull=True,
        session_id=session_id,
        status=SeatHoldStatus.HELD,
        expires_at__lte=now,
    ).update(status=SeatHoldStatus.EXPIRED)

    if orphan_expired_count:
        logger.info(
            'seat_holds_expired_without_booking session_id=%s count=%s expired_at=%s',
            session_id,
            orphan_expired_count,
            now.isoformat(),
        )

    return expired_booking_ids


def count_available_session_seats(session, *, now=None) -> int:
    snapshot = get_session_seat_status_snapshot(session, now=now)
    return snapshot['available_seats']


def build_session_seat_map(session, user=None, *, now=None):
    snapshot = get_session_seat_status_snapshot(session, user=user, now=now)

    return {
        'hall_id': session.hall.id,
        'hall_name': session.hall.name,
        'schema': snapshot['schema'],
        'seats': snapshot['seats'],
        'polling_interval': settings.SEAT_POLLING_INTERVAL_SECONDS,
        'available_seats': snapshot['available_seats'],
        'server_time': snapshot['server_time'],
    }


def get_session_seat_status_snapshot(session, user=None, *, now=None):
    server_time = now or timezone.now()
    layout = get_hall_layout(session.hall)
    active_holds = _active_holds_by_seat(session, now=server_time)
    booked_seats = _booked_seats(session)
    price_payload = get_price_payload(session)
    seats = []
    available_seats = 0
    user_id = getattr(user, 'id', None) if getattr(user, 'is_authenticated', False) else None

    for row_data in layout['rows']:
        row_number = row_data['row']
        for seat_data in row_data['seats']:
            seat_number = seat_data['number']
            seat_type = seat_data['type']
            seat_key = (row_number, seat_number)
            status = 'available'
            held_by_me = False
            expires_at = None

            if seat_key in layout['disabled_seat_set']:
                status = 'disabled'
            elif seat_key in booked_seats:
                status = 'booked'
            elif seat_key in active_holds:
                hold = active_holds[seat_key]
                status = 'held'
                held_by_me = user_id is not None and hold.user_id == user_id
                expires_at = hold.expires_at
            else:
                available_seats += 1

            seats.append(
                {
                    'row': row_number,
                    'number': seat_number,
                    'type': seat_type,
                    'status': status,
                    'held_by_me': held_by_me,
                    'expires_at': expires_at,
                    'price': price_payload,
                }
            )

    return {
        'schema': {
            'rows': layout['rows'],
            'disabled_seats': layout['disabled_seats'],
        },
        'seats': seats,
        'available_seats': available_seats,
        'server_time': server_time,
    }


def _active_holds_by_seat(session, *, now):
    active_holds = {}

    for hold in session.seat_holds.all():
        if hold.status != SeatHoldStatus.HELD:
            continue
        if hold.expires_at <= now:
            continue
        active_holds[(hold.seat_row, hold.seat_number)] = hold

    return active_holds


def _booked_seats(session):
    booked_seats = set()

    for hold in session.seat_holds.all():
        if hold.status == SeatHoldStatus.BOOKED:
            booked_seats.add((hold.seat_row, hold.seat_number))

    for booking in session.bookings.all():
        for seat in booking.seats.all():
            booked_seats.add((seat.seat_row, seat.seat_number))

    return booked_seats

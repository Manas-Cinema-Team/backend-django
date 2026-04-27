from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.screenings.models import MovieSession
from apps.screenings.services import get_hall_layout, get_primary_price

from .models import Booking, BookingSeat, BookingStatus, PaymentStatus, SeatHold, SeatHoldStatus
from .seat_status import cleanup_expired_session_holds


HOLD_DURATION = timedelta(minutes=10)


class BookingWorkflowError(Exception):
    def __init__(self, error: str, message: str, status_code: int, details: dict | None = None):
        super().__init__(message)
        self.error = error
        self.message = message
        self.status_code = status_code
        self.details = details


def get_booking_for_user(booking_id: int, user) -> Booking:
    booking = Booking.objects.filter(pk=booking_id).select_related('session').first()
    if booking is None:
        raise BookingWorkflowError('NOT_FOUND', 'Бронирование не найдено', 404)
    if booking.user_id != user.id:
        raise BookingWorkflowError('FORBIDDEN', 'Нет доступа к этой брони.', 403)

    cleanup_expired_session_holds(booking.session_id)
    return _booking_response_queryset().get(pk=booking_id)


@transaction.atomic
def create_booking_hold(*, user, session_id: int, seats: list[dict]) -> Booking:
    now = timezone.now()
    session = _get_locked_session(session_id)
    if session is None:
        raise BookingWorkflowError('NOT_FOUND', 'Сеанс не найден', 404)

    cleanup_expired_session_holds(session.id, now=now)
    seat_catalog, disabled_seats = _seat_catalog(session.hall)
    requested_seats = _normalize_seat_coordinates(seats)

    invalid_seats = [seat for seat in requested_seats if (seat['row'], seat['number']) not in seat_catalog]
    if invalid_seats:
        raise BookingWorkflowError(
            'VALIDATION_ERROR',
            'Некорректные места в запросе.',
            400,
            {'seats': invalid_seats},
        )

    disabled_conflicts = [
        seat for seat in requested_seats if (seat['row'], seat['number']) in disabled_seats
    ]
    if disabled_conflicts:
        raise BookingWorkflowError(
            'VALIDATION_ERROR',
            'Нельзя бронировать недоступные места.',
            400,
            {'seats': disabled_conflicts},
        )

    conflicting_seats = _conflicting_seats(session.id, requested_seats)
    if conflicting_seats:
        raise BookingWorkflowError(
            'SEAT_HELD',
            'Одно или несколько мест уже заняты.',
            409,
            {'seats': conflicting_seats},
        )

    price = get_primary_price(session)
    if price is None:
        raise BookingWorkflowError(
            'VALIDATION_ERROR',
            'Для сеанса не настроена цена.',
            400,
            {'session_id': ['Для сеанса не настроена цена.']},
        )

    expires_at = now + HOLD_DURATION
    total_amount = price.amount * Decimal(len(requested_seats))
    booking = Booking.objects.create(
        session=session,
        user=user,
        total_amount=total_amount,
        currency=price.currency,
        booking_status=BookingStatus.PENDING,
        payment_status=PaymentStatus.PENDING,
        expires_at=expires_at,
    )
    SeatHold.objects.bulk_create(
        [
            SeatHold(
                booking=booking,
                session=session,
                user=user,
                seat_row=seat['row'],
                seat_number=seat['number'],
                expires_at=expires_at,
                status=SeatHoldStatus.HELD,
            )
            for seat in requested_seats
        ]
    )

    return _booking_response_queryset().get(pk=booking.id)


def confirm_booking(*, booking_id: int, user) -> Booking:
    workflow_error = None
    result_booking_id = booking_id

    with transaction.atomic():
        booking = _lock_booking_for_user(booking_id, user)
        now = timezone.now()
        cleanup_expired_session_holds(booking.session_id, now=now)
        booking = _booking_response_queryset().get(pk=booking.id)
        result_booking_id = booking.id

        if booking.booking_status != BookingStatus.CONFIRMED:
            if _is_booking_expired(booking, now):
                _expire_booking(booking.id)
                workflow_error = BookingWorkflowError('HOLD_EXPIRED', 'Время ожидания истекло', 409)
            elif booking.booking_status != BookingStatus.PENDING:
                workflow_error = BookingWorkflowError(
                    'BOOKING_NOT_ACTIVE',
                    'Бронь уже недоступна для подтверждения.',
                    409,
                )
            else:
                holds = list(
                    booking.seat_holds.filter(status=SeatHoldStatus.HELD).order_by('seat_row', 'seat_number')
                )
                if not holds:
                    _expire_booking(booking.id)
                    workflow_error = BookingWorkflowError('HOLD_EXPIRED', 'Время ожидания истекло', 409)
                else:
                    existing_seats = {
                        (seat.seat_row, seat.seat_number)
                        for seat in booking.seats.all()
                    }
                    seat_price = _per_seat_price(booking, len(holds))
                    seats_to_create = []
                    for hold in holds:
                        if (hold.seat_row, hold.seat_number) in existing_seats:
                            continue
                        seats_to_create.append(
                            BookingSeat(
                                booking=booking,
                                seat_row=hold.seat_row,
                                seat_number=hold.seat_number,
                                price_at_booking=seat_price,
                            )
                        )

                    if seats_to_create:
                        BookingSeat.objects.bulk_create(seats_to_create)

                    booking.seat_holds.filter(status=SeatHoldStatus.HELD).update(status=SeatHoldStatus.BOOKED)
                    booking.booking_status = BookingStatus.CONFIRMED
                    booking.payment_status = PaymentStatus.PAID
                    booking.confirmed_at = now
                    booking.save(update_fields=['booking_status', 'payment_status', 'confirmed_at'])

    if workflow_error is not None:
        raise workflow_error

    return _booking_response_queryset().get(pk=result_booking_id)


@transaction.atomic
def cancel_booking(*, booking_id: int, user) -> None:
    booking = _lock_booking_for_user(booking_id, user)
    now = timezone.now()
    cleanup_expired_session_holds(booking.session_id, now=now)
    booking.refresh_from_db()

    if booking.booking_status in {BookingStatus.CANCELLED, BookingStatus.EXPIRED}:
        return

    booking.booking_status = BookingStatus.CANCELLED
    booking.payment_status = PaymentStatus.CANCELLED
    booking.save(update_fields=['booking_status', 'payment_status'])
    booking.seat_holds.filter(
        status__in=[SeatHoldStatus.HELD, SeatHoldStatus.BOOKED],
    ).update(status=SeatHoldStatus.CANCELLED)


def _booking_response_queryset():
    return Booking.objects.select_related(
        'session',
        'session__movie',
        'session__hall',
    ).prefetch_related(
        'seat_holds',
        'seats',
        'session__ticket_prices',
    )


def _lock_booking_for_user(booking_id: int, user) -> Booking:
    booking = Booking.objects.filter(pk=booking_id).select_related('session').first()
    if booking is None:
        raise BookingWorkflowError('NOT_FOUND', 'Бронирование не найдено', 404)
    if booking.user_id != user.id:
        raise BookingWorkflowError('FORBIDDEN', 'Нет доступа к этой брони.', 403)

    _lock_session(booking.session_id, require_active=False)
    return _booking_response_queryset().select_for_update().get(pk=booking_id)


def _get_locked_session(session_id: int) -> MovieSession | None:
    return _lock_session(session_id, require_active=True)


def _lock_session(session_id: int, *, require_active: bool) -> MovieSession | None:
    queryset = (
        MovieSession.objects.select_for_update()
        .select_related('movie', 'hall')
        .prefetch_related('ticket_prices')
        .filter(pk=session_id)
    )

    if require_active:
        queryset = queryset.filter(is_active=True)

    return queryset.first()


def _seat_catalog(hall):
    layout = get_hall_layout(hall)
    catalog = {}

    for row_data in layout['rows']:
        row_number = row_data['row']
        for seat_data in row_data['seats']:
            catalog[(row_number, seat_data['number'])] = seat_data['type']

    disabled_set = {
        (seat['row'], seat['number'])
        for seat in layout['disabled_seats']
    }
    return catalog, disabled_set


def _normalize_seat_coordinates(seats: list[dict]) -> list[dict]:
    normalized = []
    for seat in seats:
        normalized.append(
            {
                'row': seat['row'],
                'number': seat['number'],
            }
        )
    normalized.sort(key=lambda item: (item['row'], item['number']))
    return normalized


def _conflicting_seats(session_id: int, requested_seats: list[dict]) -> list[dict]:
    requested_coordinates = {
        (seat['row'], seat['number'])
        for seat in requested_seats
    }
    conflicts = set()

    active_holds = SeatHold.objects.filter(
        session_id=session_id,
        status__in=[SeatHoldStatus.HELD, SeatHoldStatus.BOOKED],
        seat_row__in=[row for row, _ in requested_coordinates],
        seat_number__in=[number for _, number in requested_coordinates],
    )
    for hold in active_holds:
        coordinate = (hold.seat_row, hold.seat_number)
        if coordinate in requested_coordinates:
            conflicts.add(coordinate)

    confirmed_seats = BookingSeat.objects.filter(
        booking__session_id=session_id,
        booking__booking_status=BookingStatus.CONFIRMED,
        seat_row__in=[row for row, _ in requested_coordinates],
        seat_number__in=[number for _, number in requested_coordinates],
    )
    for seat in confirmed_seats:
        coordinate = (seat.seat_row, seat.seat_number)
        if coordinate in requested_coordinates:
            conflicts.add(coordinate)

    return [
        {'row': row, 'number': number}
        for row, number in sorted(conflicts)
    ]


def _per_seat_price(booking: Booking, seat_count: int) -> Decimal:
    if seat_count <= 0:
        return Decimal('0.00')
    return booking.total_amount / Decimal(seat_count)


def _is_booking_expired(booking: Booking, now) -> bool:
    if booking.booking_status == BookingStatus.EXPIRED:
        return True
    return booking.expires_at is not None and booking.expires_at <= now


def _expire_booking(booking_id: int) -> None:
    Booking.objects.filter(
        pk=booking_id,
        booking_status=BookingStatus.PENDING,
    ).update(
        booking_status=BookingStatus.EXPIRED,
        payment_status=PaymentStatus.CANCELLED,
    )
    SeatHold.objects.filter(
        booking_id=booking_id,
        status=SeatHoldStatus.HELD,
    ).update(status=SeatHoldStatus.EXPIRED)

from collections import defaultdict
from decimal import Decimal

from django.utils import timezone

from apps.bookings.models import SeatHoldStatus
from apps.pricing.models import TicketCurrency


POLLING_INTERVAL_SECONDS = 5


def get_primary_price(session):
    prices = list(session.ticket_prices.all())
    if not prices:
        return None

    for price in prices:
        if price.currency == TicketCurrency.KGS:
            return price

    return prices[0]


def get_price_payload(session, seat_type: str | None = None):
    del seat_type
    price = get_primary_price(session)
    if price is None:
        return None

    return {
        'amount': price.amount,
        'currency': price.currency,
    }


def build_session_seat_map(session, user=None):
    hall = session.hall
    metadata = hall.schema_metadata if isinstance(hall.schema_metadata, dict) else {}
    disabled_seats, disabled_payload = _extract_disabled_seats(metadata)
    rows_payload = _normalize_rows(hall, metadata)
    active_holds = _active_holds_by_seat(session)
    booked_seats = _booked_seats(session)

    seats = []
    available_seats = 0
    user_id = getattr(user, 'id', None) if getattr(user, 'is_authenticated', False) else None

    for row_data in rows_payload:
        row_number = row_data['row']
        for seat_data in row_data['seats']:
            seat_number = seat_data['number']
            seat_type = seat_data['type']
            seat_key = (row_number, seat_number)
            status = 'available'
            held_by_me = False
            expires_at = None

            if seat_key in disabled_seats:
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
                    'price': get_price_payload(session, seat_type=seat_type),
                }
            )

    return {
        'hall_id': hall.id,
        'hall_name': hall.name,
        'schema': {
            'rows': rows_payload,
            'disabled_seats': disabled_payload,
        },
        'seats': seats,
        'polling_interval': POLLING_INTERVAL_SECONDS,
        'available_seats': available_seats,
    }


def _extract_disabled_seats(metadata):
    disabled_seat_set = set()
    disabled_payload = []

    for seat in metadata.get('disabled_seats', []):
        row = seat.get('row')
        number = seat.get('number')
        if not _is_positive_int(row) or not _is_positive_int(number):
            continue

        seat_key = (row, number)
        if seat_key in disabled_seat_set:
            continue

        disabled_seat_set.add(seat_key)
        disabled_payload.append({'row': row, 'number': number})

    return disabled_seat_set, sorted(disabled_payload, key=lambda item: (item['row'], item['number']))


def _normalize_rows(hall, metadata):
    configured_rows = defaultdict(dict)

    for row_data in metadata.get('rows', []):
        row_number = row_data.get('row')
        if not _is_positive_int(row_number):
            continue

        for seat in row_data.get('seats', []):
            seat_number = seat.get('number')
            if not _is_positive_int(seat_number):
                continue
            configured_rows[row_number][seat_number] = {
                'number': seat_number,
                'type': seat.get('type') or 'standard',
            }

    for seat in metadata.get('seats', []):
        row_number = seat.get('row')
        seat_number = seat.get('number')
        if not _is_positive_int(row_number) or not _is_positive_int(seat_number):
            continue
        configured_rows[row_number][seat_number] = {
            'number': seat_number,
            'type': seat.get('type') or 'standard',
        }

    rows_payload = []
    for row_number in range(1, hall.rows + 1):
        row_seats = configured_rows.get(row_number, {})
        max_number = max(row_seats.keys(), default=0)
        upper_bound = max(hall.seats_per_row, max_number)

        normalized_seats = []
        for seat_number in range(1, upper_bound + 1):
            seat_data = row_seats.get(
                seat_number,
                {'number': seat_number, 'type': 'standard'},
            )
            normalized_seats.append(seat_data)

        rows_payload.append(
            {
                'row': row_number,
                'seats': normalized_seats,
            }
        )

    return rows_payload


def _active_holds_by_seat(session):
    now = timezone.now()
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


def _is_positive_int(value):
    return isinstance(value, int) and value > 0

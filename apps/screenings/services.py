from collections import defaultdict
from decimal import Decimal

from apps.pricing.models import TicketCurrency


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


def get_hall_layout(hall):
    metadata = hall.schema_metadata if isinstance(hall.schema_metadata, dict) else {}
    disabled_seat_set, disabled_payload = _extract_disabled_seats(metadata)
    rows_payload = _normalize_rows(hall, metadata)

    return {
        'rows': rows_payload,
        'disabled_seats': disabled_payload,
        'disabled_seat_set': disabled_seat_set,
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


def _is_positive_int(value):
    return isinstance(value, int) and value > 0

from decimal import Decimal

from django.utils import timezone
from rest_framework import serializers

from apps.screenings.services import get_hall_layout

from .models import Booking, BookingStatus, SeatHoldStatus


INTERNAL_BOOKING_STATUS_TO_API = {
    BookingStatus.PENDING: 'draft',
    BookingStatus.CONFIRMED: 'confirmed',
    BookingStatus.CANCELLED: 'cancelled',
    BookingStatus.EXPIRED: 'expired',
}


class RequestedSeatSerializer(serializers.Serializer):
    row = serializers.IntegerField(min_value=1)
    number = serializers.IntegerField(min_value=1)


class BookingCreateSerializer(serializers.Serializer):
    session_id = serializers.IntegerField(min_value=1)
    seats = RequestedSeatSerializer(many=True, allow_empty=False)

    def validate_seats(self, value):
        unique_coordinates = set()
        duplicates = []

        for seat in value:
            coordinate = (seat['row'], seat['number'])
            if coordinate in unique_coordinates:
                duplicates.append({'row': seat['row'], 'number': seat['number']})
                continue
            unique_coordinates.add(coordinate)

        if duplicates:
            raise serializers.ValidationError(
                'Список мест содержит дубли.',
                code='duplicate_seats',
            )

        return value


class BookingConfirmSerializer(serializers.Serializer):
    payment_mock = serializers.BooleanField(required=False)


class BookingSessionMovieSerializer(serializers.Serializer):
    title = serializers.CharField()


class BookingSessionHallSerializer(serializers.Serializer):
    name = serializers.CharField()


class BookingSessionSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    movie = BookingSessionMovieSerializer()
    hall = BookingSessionHallSerializer()
    start_datetime = serializers.DateTimeField()


class BookingSeatResponseSerializer(serializers.Serializer):
    row = serializers.IntegerField()
    number = serializers.IntegerField()
    type = serializers.CharField()
    price_at_booking = serializers.DecimalField(max_digits=10, decimal_places=2, coerce_to_string=False)


class BookingResponseSerializer(serializers.ModelSerializer):
    session = serializers.SerializerMethodField()
    seats = serializers.SerializerMethodField()
    currency = serializers.SerializerMethodField()
    booking_status = serializers.SerializerMethodField()
    expires_at = serializers.SerializerMethodField()
    server_time = serializers.SerializerMethodField()
    total_amount = serializers.DecimalField(max_digits=10, decimal_places=2, coerce_to_string=False)
    confirmed_at = serializers.DateTimeField(allow_null=True)

    class Meta:
        model = Booking
        fields = (
            'id',
            'session',
            'seats',
            'total_amount',
            'currency',
            'booking_status',
            'payment_status',
            'expires_at',
            'server_time',
            'confirmed_at',
            'created_at',
        )

    def get_session(self, obj):
        return BookingSessionSerializer(
            {
                'id': obj.session_id,
                'movie': {'title': obj.session.movie.title},
                'hall': {'name': obj.session.hall.name},
                'start_datetime': obj.session.start_datetime,
            }
        ).data

    def get_seats(self, obj):
        seat_type_map = _seat_type_map(obj.session.hall)
        confirmed_seats = list(obj.seats.all())

        if confirmed_seats:
            payload = [
                {
                    'row': seat.seat_row,
                    'number': seat.seat_number,
                    'type': seat_type_map.get((seat.seat_row, seat.seat_number), 'standard'),
                    'price_at_booking': seat.price_at_booking,
                }
                for seat in confirmed_seats
            ]
        else:
            holds = [
                hold
                for hold in obj.seat_holds.all()
                if hold.status in {
                    SeatHoldStatus.HELD,
                    SeatHoldStatus.BOOKED,
                    SeatHoldStatus.CANCELLED,
                    SeatHoldStatus.EXPIRED,
                }
            ]
            seat_price = _pending_seat_price(obj, len(holds))
            payload = [
                {
                    'row': hold.seat_row,
                    'number': hold.seat_number,
                    'type': seat_type_map.get((hold.seat_row, hold.seat_number), 'standard'),
                    'price_at_booking': seat_price,
                }
                for hold in holds
            ]

        payload.sort(key=lambda item: (item['row'], item['number']))
        return BookingSeatResponseSerializer(payload, many=True).data

    def get_currency(self, obj):
        if obj.currency:
            return obj.currency

        price = next(iter(obj.session.ticket_prices.all()), None)
        return price.currency if price is not None else 'KGS'

    def get_booking_status(self, obj):
        return INTERNAL_BOOKING_STATUS_TO_API.get(obj.booking_status, obj.booking_status)

    def get_expires_at(self, obj):
        if obj.expires_at is not None:
            return obj.expires_at

        hold = next(iter(obj.seat_holds.all()), None)
        return hold.expires_at if hold is not None else None

    def get_server_time(self, obj):
        return self.context.get('server_time') or timezone.now()


def _seat_type_map(hall):
    layout = get_hall_layout(hall)
    mapping = {}

    for row_data in layout['rows']:
        row = row_data['row']
        for seat in row_data['seats']:
            mapping[(row, seat['number'])] = seat['type']

    return mapping


def _pending_seat_price(booking, seat_count: int) -> Decimal:
    if seat_count <= 0:
        return Decimal('0.00')

    return booking.total_amount / Decimal(seat_count)

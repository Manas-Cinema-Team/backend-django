from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models import Q


class SeatHoldStatus(models.TextChoices):
    HELD = 'held', 'Held'
    BOOKED = 'booked', 'Booked'
    EXPIRED = 'expired', 'Expired'
    CANCELLED = 'cancelled', 'Cancelled'


class BookingStatus(models.TextChoices):
    PENDING = 'pending', 'Pending'
    CONFIRMED = 'confirmed', 'Confirmed'
    EXPIRED = 'expired', 'Expired'
    CANCELLED = 'cancelled', 'Cancelled'


class PaymentStatus(models.TextChoices):
    PENDING = 'pending', 'Pending'
    PAID = 'paid', 'Paid'
    FAILED = 'failed', 'Failed'
    CANCELLED = 'cancelled', 'Cancelled'


class SeatHold(models.Model):
    session = models.ForeignKey(
        'screenings.MovieSession',
        on_delete=models.CASCADE,
        related_name='seat_holds',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='seat_holds',
    )
    seat_row = models.PositiveSmallIntegerField()
    seat_number = models.PositiveSmallIntegerField()
    expires_at = models.DateTimeField(db_index=True)
    status = models.CharField(
        max_length=10,
        choices=SeatHoldStatus.choices,
        default=SeatHoldStatus.HELD,
        db_index=True,
    )

    class Meta:
        ordering = ['expires_at', 'seat_row', 'seat_number']
        indexes = [
            models.Index(fields=['session', 'status'], name='bk_hold_session_status_idx'),
            models.Index(fields=['session', 'expires_at'], name='bk_hold_session_expires_idx'),
            models.Index(fields=['user', 'status'], name='bookings_hold_user_status_idx'),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(seat_row__gt=0),
                name='bookings_hold_row_gt_zero',
            ),
            models.CheckConstraint(
                condition=Q(seat_number__gt=0),
                name='bookings_hold_seat_gt_zero',
            ),
            models.UniqueConstraint(
                fields=['session', 'seat_row', 'seat_number'],
                condition=Q(status=SeatHoldStatus.HELD),
                name='bookings_unique_active_hold_seat',
            ),
            models.UniqueConstraint(
                fields=['session', 'seat_row', 'seat_number'],
                condition=Q(status=SeatHoldStatus.BOOKED),
                name='bookings_unique_booked_hold_seat',
            ),
        ]

    def __str__(self):
        return f'{self.session} seat {self.seat_row}-{self.seat_number}'


class Booking(models.Model):
    session = models.ForeignKey(
        'screenings.MovieSession',
        on_delete=models.PROTECT,
        related_name='bookings',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='bookings',
    )
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    booking_status = models.CharField(
        max_length=10,
        choices=BookingStatus.choices,
        default=BookingStatus.PENDING,
        db_index=True,
    )
    payment_status = models.CharField(
        max_length=10,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
        db_index=True,
    )
    confirmed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'booking_status'], name='bookings_user_status_idx'),
            models.Index(fields=['session', 'booking_status'], name='bookings_session_status_idx'),
            models.Index(fields=['payment_status', 'created_at'], name='bookings_payment_created_idx'),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(total_amount__gte=Decimal('0.00')),
                name='bookings_total_amount_gte_zero',
            ),
        ]

    def __str__(self):
        return f'Booking #{self.pk} for session {self.session_id}'


class BookingSeat(models.Model):
    booking = models.ForeignKey(
        Booking,
        on_delete=models.CASCADE,
        related_name='seats',
    )
    seat_row = models.PositiveSmallIntegerField()
    seat_number = models.PositiveSmallIntegerField()
    price_at_booking = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        ordering = ['seat_row', 'seat_number']
        indexes = [
            models.Index(fields=['seat_row', 'seat_number'], name='bookings_seat_coordinates_idx'),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(seat_row__gt=0),
                name='bookings_seat_row_gt_zero',
            ),
            models.CheckConstraint(
                condition=Q(seat_number__gt=0),
                name='bookings_seat_number_gt_zero',
            ),
            models.CheckConstraint(
                condition=Q(price_at_booking__gte=Decimal('0.00')),
                name='bookings_seat_price_gte_zero',
            ),
            models.UniqueConstraint(
                fields=['booking', 'seat_row', 'seat_number'],
                name='bookings_unique_booking_seat',
            ),
        ]

    def __str__(self):
        return f'Booking #{self.booking_id}: {self.seat_row}-{self.seat_number}'

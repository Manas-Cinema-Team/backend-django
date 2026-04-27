from django.contrib import admin

from .models import Booking, BookingSeat, SeatHold


class BookingSeatInline(admin.TabularInline):
    model = BookingSeat
    extra = 0
    min_num = 0


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'session',
        'user',
        'total_amount',
        'currency',
        'booking_status',
        'payment_status',
        'expires_at',
        'created_at',
        'seat_count',
    )
    list_filter = ('booking_status', 'payment_status', 'session')
    search_fields = ('user__email', 'session__movie__title', 'session__hall__name')
    autocomplete_fields = ('session', 'user')
    list_select_related = ('session', 'session__movie', 'session__hall', 'user')
    readonly_fields = ('created_at', 'confirmed_at', 'expires_at')
    ordering = ('-created_at',)
    date_hierarchy = 'created_at'
    inlines = [BookingSeatInline]

    @admin.display(description='Seats')
    def seat_count(self, obj):
        return obj.seats.count()


@admin.register(SeatHold)
class SeatHoldAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'session',
        'user',
        'seat_row',
        'seat_number',
        'status',
        'expires_at',
    )
    list_filter = ('status', 'session')
    search_fields = ('user__email', 'session__movie__title', 'session__hall__name')
    autocomplete_fields = ('session', 'user')
    list_select_related = ('session', 'session__movie', 'session__hall', 'user')
    ordering = ('expires_at',)
    date_hierarchy = 'expires_at'


@admin.register(BookingSeat)
class BookingSeatAdmin(admin.ModelAdmin):
    list_display = ('booking', 'seat_row', 'seat_number', 'price_at_booking')
    search_fields = ('booking__user__email', 'booking__session__movie__title')
    autocomplete_fields = ('booking',)
    list_select_related = ('booking', 'booking__user', 'booking__session', 'booking__session__movie')
    ordering = ('booking', 'seat_row', 'seat_number')

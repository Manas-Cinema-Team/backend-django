from django.contrib import admin

from apps.pricing.models import TicketPrice

from .models import MovieSession


class TicketPriceInline(admin.TabularInline):
    model = TicketPrice
    extra = 0
    min_num = 0


@admin.register(MovieSession)
class MovieSessionAdmin(admin.ModelAdmin):
    list_display = (
        'movie',
        'hall',
        'start_datetime',
        'end_datetime',
        'is_active',
        'price_count',
    )
    list_filter = ('is_active', 'hall', 'movie')
    search_fields = ('movie__title', 'hall__name')
    autocomplete_fields = ('movie', 'hall')
    list_select_related = ('movie', 'hall')
    date_hierarchy = 'start_datetime'
    ordering = ('start_datetime',)
    inlines = [TicketPriceInline]

    @admin.display(description='Prices')
    def price_count(self, obj):
        return obj.ticket_prices.count()
